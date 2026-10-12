#!/usr/bin/env python3
# copyright by berlonak
# telegram: @Kilax123
"""Prepare a portable, indexed Telegram Archive folder on Windows; activate on Linux.

No Python virtualenvs/binaries are copied across operating systems. The SQLite
index, relative media references and Argon2id password hash *are* portable.
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOKEN = "@TGARCHIVE_BUNDLE@/"
VERSION = 1


def fail(message: str) -> None:
    raise SystemExit("Ошибка: " + message)


def canonical(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def in_tree(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def file_inventory(root: Path) -> dict[str, int]:
    """Inventory source files without loading them; reject links escaping a portable archive.

    Files referenced by neither JSON nor the HTML viewer are preserved as well.
    Counts and total byte size detect incomplete folder transfers, not same-size
    corruption. The JSON file itself is also individually SHA256-verified.
    """
    count, size = 0, 0
    for base, dirs, files in os.walk(root, followlinks=False):
        where = Path(base)
        for name in dirs:
            if (where / name).is_symlink():
                fail(f"В экспорте символическая ссылка на папку: {where / name}")
        for name in files:
            path = where / name
            if path.is_symlink() or not path.is_file():
                fail(f"В экспорте ссылка или нестандартный файл: {path}")
            count += 1
            size += path.stat().st_size
    return {"file_count": count, "total_bytes": size}


def copy_application(bundle: Path) -> None:
    target = bundle / "app"
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "tgarchive", target / "tgarchive", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copy2(ROOT / "pyproject.toml", target / "pyproject.toml")
    # pyproject.toml references these files; the license must travel with the code.
    for meta in ("README.md", "LICENSE", "NOTICE"):
        shutil.copy2(ROOT / meta, target / meta)
    for extra in ("Dockerfile", ".dockerignore"):
        shutil.copy2(ROOT / extra, target / extra)
    # The ready bundle must launch locally without separately downloading hotfixes.
    for starter in ("START-LOCAL.bat", "start-local.py", "RESET-PASSWORD.bat"):
        shutil.copy2(ROOT / starter, bundle / starter)
    deploy = bundle / "deploy"
    deploy.mkdir(exist_ok=True)
    for name in ["configure-https-ip.sh", "tgarchive-cert-renew.service", "tgarchive-cert-renew.timer"]:
        shutil.copy2(ROOT / "deploy" / name, deploy / name)
    shutil.copy2(ROOT / "deploy" / "install-bundle.sh", deploy / "install-bundle.sh")
    shutil.copy2(ROOT / "bundletool.py", bundle / "bundletool.py")
    shutil.copy2(ROOT / "BUNDLE-README.md", bundle / "README.md")
    shutil.copy2(ROOT / "SERVER-RU.md", bundle / "SERVER-RU.md")
    (deploy / "docker").mkdir(exist_ok=True)
    shutil.copy2(ROOT / "deploy" / "docker" / "compose.yaml", deploy / "docker" / "compose.yaml")


def prompt_password_gui(confirm: bool) -> str:
    """Windows-friendly password input with normal Ctrl+V / clipboard pasting.

    Unlike getpass() in some CMD hosts, Tk Entry widgets reliably accept paste.
    Cancel never mutates the bundle. No plaintext password goes into argv or files.
    """
    try:
        import tkinter as tk
        from tkinter import simpledialog, messagebox
    except ImportError:
        fail("Python установлен без Tkinter. Установи Python с компонентом Tcl/Tk "
             "либо запусти команду без --gui (ввод в консоли, не через Shift+Insert).")
    root = tk.Tk()
    root.withdraw()
    try:
        for _ in range(3):
            password = simpledialog.askstring(
                "Telegram Archive — пароль", "Вставь пароль через Ctrl+V (не менее 12 символов):",
                show="*", parent=root,
            )
            if password is None:
                fail("Ввод пароля отменён. Экспорт не будет перемещён.")
            if len(password) < 12:
                messagebox.showerror("Пароль", "Пароль должен содержать минимум 12 символов.", parent=root)
                continue
            if not confirm:
                return password
            again = simpledialog.askstring(
                "Telegram Archive — подтверждение", "Вставь ТОТ ЖЕ пароль ещё раз через Ctrl+V:",
                show="*", parent=root,
            )
            if again is None:
                fail("Ввод пароля отменён. Экспорт не будет перемещён.")
            if password == again:
                return password
            messagebox.showerror("Пароль", "Пароли не совпали. Повтори ввод. "
                                 "Проверь, не добавлены ли пробелы при копировании.", parent=root)
        fail("Пароль не подтверждён за три попытки. Экспорт не перемещён.")
    finally:
        root.destroy()


def preflight_password(bundle: Path, gui: bool) -> None:
    """Validate password *before* touching the (large) source directory.

    Only a password-only stub database is reused on retry. Never overwrite a
    partly imported database or silently change a previously chosen password.
    """
    from argon2 import PasswordHasher
    from tgarchive.db import initialize
    db_file = bundle / "data" / "archive.sqlite3"
    db_file.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_file, timeout=2) as conn:
        conn.row_factory = sqlite3.Row
        initialize(conn)
        if any(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
               for table in ("imports", "chats", "messages", "media", "contacts")):
            fail("В папке уже есть незавершённая база с данными. "
                 "Не перезаписывай её; остановись и проверь содержимое папки ready.")
        # No original data has been imported yet; a password-only stub from a
        # failed Move-Item attempt is safe to replace after new confirmation.
        if gui:
            password = prompt_password_gui(True)
        else:
            password = getpass.getpass("Пароль (не менее 12 символов): ")
            again = getpass.getpass("Повтори пароль: ")
            if len(password) < 12 or password != again:
                fail("Пароли не совпали или короче 12 символов. Экспорт НЕ перемещён.")
        password_hash = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2).hash(password)
        conn.execute("INSERT OR REPLACE INTO config(name,value) VALUES('password_hash',?)", (password_hash,))
        conn.commit()
    print("Пароль подтверждён и сохранён в виде хеша Argon2id. Экспорт пока не перемещён.")


def reset_password(bundle: Path, gui: bool) -> None:
    """Change password in a completed bundle without touching media or reimporting."""
    from argon2 import PasswordHasher
    db = bundle / "data" / "archive.sqlite3"
    if not db.is_file():
        fail("База не найдена. Укажи папку готового архива.")
    if gui:
        password = prompt_password_gui(True)
    else:
        password = getpass.getpass("Новый пароль: ")
        again = getpass.getpass("Повтори пароль: ")
        if password != again or len(password) < 12:
            fail("Пароли не совпали или короче 12 символов. Ничего не изменено.")
    digest = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2).hash(password)
    conn = sqlite3.connect(db, timeout=2)
    try:
        conn.execute("PRAGMA busy_timeout=2000")
        conn.execute("BEGIN IMMEDIATE")
        if not conn.execute("SELECT 1 FROM config WHERE name='password_hash'").fetchone():
            fail("Нет установленного пароля; проверь, что это готовая база.")
        conn.execute("UPDATE config SET value=? WHERE name='password_hash'", (digest,))
        conn.execute("DELETE FROM sessions")
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()
    print("Пароль обновлён; все прежние сессии сброшены. Сообщения и медиа не затронуты.")


def ask_password(db_file: Path) -> None:
    from argon2 import PasswordHasher
    from tgarchive.db import get_config, initialize
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    initialize(conn)
    if get_config(conn, "password_hash"):
        print("Пароль уже существует; сохраняю его без изменений.")
        conn.close()
        return
    password = getpass.getpass("Пароль архива (минимум 12 символов): ")
    again = getpass.getpass("Повтори пароль: ")
    if len(password) < 12 or password != again:
        conn.close()
        fail("Пароли не совпали или короче 12 символов.")
    hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
    conn.execute("INSERT OR REPLACE INTO config(name,value) VALUES('password_hash',?)", (hasher.hash(password),))
    conn.commit()
    conn.close()


def finalize_db(db_file: Path, bundle: Path) -> dict:
    """Change Windows absolute roots into a portable token, close WAL safely."""
    conn = sqlite3.connect(db_file, timeout=60)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 60000")
    imports = conn.execute("SELECT id,root FROM imports").fetchall()
    exports = bundle / "exports"
    for row in imports:
        root = canonical(row["root"])
        if not in_tree(root, exports) or not (root / "result.json").is_file():
            conn.close()
            fail(f"Импорт {row['id']} ссылается на файлы ВНЕ набора: {root}. "
                 "Пересобери набор или перемести каждый экспорт в bundle/exports/.")
        rel = root.relative_to(bundle).as_posix()
        conn.execute("UPDATE imports SET root=?,source_file=? WHERE id=?",
                     (TOKEN + rel, TOKEN + rel + "/result.json", row["id"]))
    conn.execute("DELETE FROM sessions")
    conn.commit()
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchall()
    conn.execute("PRAGMA journal_mode=DELETE").fetchall()
    stats = dict(conn.execute("SELECT COUNT(*) AS messages FROM messages").fetchone())
    stats["chats"] = conn.execute("SELECT COUNT(*) FROM chats").fetchone()[0]
    stats["media"] = conn.execute("SELECT COUNT(*) FROM media").fetchone()[0]
    stats["imports"] = len(imports)
    conn.close()
    return stats


def ensure_json(root: Path) -> Path:
    source = root / "result.json"
    if not source.is_file():
        fail(f"Не найден result.json в {root}")
    return source


def prepare(args: argparse.Namespace) -> None:
    try:
        import ijson  # noqa: F401 - demand streaming parser for large histories
        import fastapi  # noqa: F401
        import argon2  # noqa: F401
    except ImportError:
        fail("Сначала установи зависимости: python -m pip install -e .  "
             "(Для больших экспортов обязателен потоковый парсер ijson.)")
    from tgarchive.importer import import_export, import_contacts_only
    bundle = canonical(args.bundle)
    export = canonical(args.export)
    if not export.is_dir():
        fail(f"Нет каталога экспорта: {export}")
    ensure_json(export)
    if in_tree(bundle, export):
        fail("Каталог набора нельзя размещать ВНУТРИ исходного экспорта.")
    bundle.mkdir(parents=True, exist_ok=True)
    exports = bundle / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    dest = exports / args.export_name
    if not in_tree(export, exports):
        if not args.copy_export:
            fail("Экспорт находится вне bundle/exports. Для большого экспорта перемести папку "
                 "в <bundle>/exports/first-export БЕЗ копирования; или передай --copy-export "
                 "(потребуется дополнительно столько же места, сколько занимает экспорт).")
        if dest.exists():
            fail(f"Папка назначения уже есть: {dest}")
        if in_tree(bundle, export):
            fail("Нельзя копировать экспорт в самого себя.")
        print("Копирую экспорт без загрузки файлов в память; нужно свободное место не меньше объёма экспорта...")
        shutil.copytree(export, dest, symlinks=False)
        export = dest
    else:
        if not export.parent == exports:
            fail("Экспорт должен лежать непосредственно внутри bundle/exports/<название>.")
    print("Исходный Telegram-экспорт:", export)
    combined = (export / "export_results.html").is_file()
    print("Структура:", "JSON + HTML в одной папке" if combined else "JSON")
    print("Проверяю число и суммарный размер всех файлов без чтения медиа...")
    inventory = file_inventory(export)
    print("Исходных файлов:", inventory["file_count"], "Объём (байт):", inventory["total_bytes"])
    copy_application(bundle)
    manifest_path = bundle / "bundle-manifest.json"
    if manifest_path.exists():
        fail("В наборе уже есть готовый manifest. Для нового набора укажи другой каталог.")
    data = bundle / "data"
    data.mkdir(exist_ok=True)
    db_file = data / "archive.sqlite3"
    # Windows builder creates a *password-only* stub DB before moving the export.
    # Do not resume a partially imported DB here: duplicates or orphan media could
    # otherwise result after an interrupted import.
    if db_file.exists():
        with sqlite3.connect(db_file) as check:
            from tgarchive.db import initialize, get_config
            check.row_factory = sqlite3.Row
            initialize(check)
            if any(check.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                   for table in ("imports", "chats", "messages", "media", "contacts")):
                fail("В наборе уже есть частично обработанная база. "
                     "Не перезаписывай её автоматически.")
            if not get_config(check, "password_hash"):
                fail("В существующей базе нет пароля. Проверь незавершённую сборку.")
    os.environ["TGARCHIVE_DATA_DIR"] = str(data)
    ask_password(db_file)
    print("Индексирую сообщения потоково (оригинальные фото/видео не перекодируются)...")
    try:
        result = import_export(export, progress=True)
        if getattr(args, "expect_chat_records", 0) and result["chats"] != args.expect_chat_records:
            fail(f"Проверка отчёта: ожидалось {args.expect_chat_records} записей чатов, "
                 f"получено {result['chats']}. Не загружай этот пакет.")
        if getattr(args, "expect_message_records", 0) and result["messages"] != args.expect_message_records:
            fail(f"Проверка отчёта: ожидалось {args.expect_message_records} сообщений, "
                 f"получено {result['messages']}. Не загружай этот пакет.")
        print("Индексирую контакты (без медиа)...")
        contacts_count = import_contacts_only(export / "result.json")
        stats = finalize_db(db_file, bundle)
        digest = sha256(export / "result.json")
        manifest = {
            "format": "telegram-archive-portable", "format_version": VERSION,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "extracted_under": "exports/", "telegram_json_sha256": digest,
            "primary_export": export.relative_to(bundle).as_posix(), "stats": stats,
            "source_inventory": inventory,
            "import_audit": {k: result[k] for k in ("chats", "left_chats", "messages",
                                                  "media_references", "media_present", "media_missing")},
            "source_formats": ["JSON", "HTML"] if combined else ["JSON"],
            "app_version": "0.4.0", "contacts_indexed_count": contacts_count,
            "original_export_is_unchanged": True,
        }
        temporary = manifest_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(manifest_path)
        print("\nГОТОВО. Теперь загрузи ВЕСЬ каталог наборa на Linux VPS.")
        print("Уникальных чатов:", stats["chats"], "Сообщений:", stats["messages"], "Медиа:", stats["media"])
        print("Записей чатов JSON:", result["chats"], "(покинутых:", result["left_chats"], ")")
        print("Медиа-ссылок:", result["media_references"], "файлов найдено:", result["media_present"],
              "отсутствуют:", result["media_missing"])
        if result["media_missing"]:
            print("ВНИМАНИЕ: часть путей из result.json не найдена на диске. "
                  "Это могут быть невыгруженные вложения: проверь настройки экспорта.")
        print("Каталог:", bundle)
    except BaseException:
        print("Сборка не завершена: НЕ загружай этот набор. Создай новый чистый каталог.", file=sys.stderr)
        raise


def read_manifest(bundle: Path) -> dict:
    path = bundle / "bundle-manifest.json"
    if not path.is_file():
        fail("Нет bundle-manifest.json. Сборка не завершена или переданы не все файлы.")
    meta = json.loads(path.read_text(encoding="utf-8"))
    if meta.get("format") != "telegram-archive-portable" or meta.get("format_version") != VERSION:
        fail("Неизвестная версия переносимого набора.")
    return meta


def verify(bundle: Path, full: bool) -> None:
    meta = read_manifest(bundle)
    export_rel = Path(meta["primary_export"])
    if export_rel.is_absolute() or ".." in export_rel.parts or export_rel.parts[0] != "exports":
        fail("В manifest некорректный путь экспорта.")
    source = bundle / export_rel / "result.json"
    ensure_json(source.parent)
    print("Проверяю SHA256 исходного result.json (может занять время)...")
    if sha256(source) != meta["telegram_json_sha256"]:
        fail("SHA256 result.json не совпадает: файл изменён или передан не полностью.")
    if meta.get("source_inventory"):
        print("Проверяю полный список файлов по числу и объёму...")
        actual_inventory = file_inventory(source.parent)
        if actual_inventory != meta["source_inventory"]:
            fail(f"Неполная передача файлов: ожидалось {meta['source_inventory']}, "
                 f"получено {actual_inventory}")
    db_file = bundle / "data" / "archive.sqlite3"
    conn = sqlite3.connect(f"file:{db_file.as_posix()}?mode=ro", uri=True)
    qc = conn.execute("PRAGMA quick_check").fetchone()[0]
    if qc != "ok":
        fail(f"Ошибка базы SQLite: {qc}")
    roots = {}
    for id_, raw in conn.execute("SELECT id,root FROM imports"):
        if raw.startswith(TOKEN):
            rel = Path(raw[len(TOKEN):])
            if rel.is_absolute() or ".." in rel.parts or rel.parts[0] != "exports":
                fail("Некорректная переносимая ссылка в SQLite")
            roots[id_] = bundle / rel
        else:
            root = canonical(raw)
            if not in_tree(root, bundle / "exports"):
                fail(f"SQLite импорт ссылается за пределы набора: {root}")
            roots[id_] = root
    for root in roots.values():
        ensure_json(root)
    if full:
        print("Проверяю наличие КАЖДОГО медиафайла (на большом экспорте это может быть долго)...")
        missing = []
        seen = 0
        for import_id, relpath in conn.execute("SELECT import_id,relpath FROM media"):
            root = roots[import_id]
            target = canonical(root / relpath)
            if not in_tree(target, canonical(root)) or not target.is_file():
                if len(missing) < 10:
                    missing.append(str(target))
            seen += 1
        if missing:
            fail("Не найдены медиа (примеры): " + "; ".join(missing))
        print(f"Файлов, упомянутых в SQLite: {seen:,}")
    else:
        missing = []
        for import_id, relpath in conn.execute("SELECT import_id,relpath FROM media LIMIT 100"):
            root = roots[import_id]
            target = canonical(root / relpath)
            if not in_tree(target, canonical(root)) or not target.is_file():
                missing.append(str(target))
        if missing:
            fail("Не найден один из первых 100 медиа: " + "; ".join(missing[:4]))
    conn.close()
    print("Проверка пройдена.")


def activate(bundle: Path) -> None:
    read_manifest(bundle)
    db = bundle / "data" / "archive.sqlite3"
    conn = sqlite3.connect(db, timeout=60)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("BEGIN IMMEDIATE")
        rows = conn.execute("SELECT id,root FROM imports").fetchall()
        for row in rows:
            raw = row["root"]
            if raw.startswith(TOKEN):
                rel = Path(raw[len(TOKEN):])
                if rel.is_absolute() or ".." in rel.parts or rel.parts[0] != "exports":
                    fail("Подозрительная ссылка в SQLite: " + raw)
                root = canonical(bundle / rel)
                if not in_tree(root, bundle / "exports"):
                    fail("Путь экспорта выходит за пределы набора: " + str(root))
                ensure_json(root)
                conn.execute("UPDATE imports SET root=?,source_file=? WHERE id=?",
                             (str(root), str(root / "result.json"), row["id"]))
            elif not in_tree(canonical(raw), bundle / "exports"):
                fail("Неожиданная ссылка на экспорт за пределами пакета: " + raw)
        conn.execute("DELETE FROM sessions")
        conn.commit()
        print("SQLite пути привязаны к серверу. Пароль и полнотекстовый индекс сохранены.")
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def pack(bundle: Path, output: Path) -> None:
    """Optional one-file TAR; for large bundles a resumable directory sync is preferred."""
    verify(bundle, full=False)
    output = output.expanduser().absolute()
    if in_tree(output, bundle):
        fail("Нельзя создавать .tar ВНУТРИ упаковываемого каталога.")
    if output.exists():
        fail("Файл уже существует: " + str(output))
    output.parent.mkdir(parents=True, exist_ok=True)
    print("Создаю один TAR без сжатия: медиа уже сжаты. Нужно дополнительное место размером с весь набор.")
    try:
        with tarfile.open(output, mode="w|") as archive:
            archive.add(bundle, arcname="tgarchive", recursive=True)
    except BaseException:
        output.unlink(missing_ok=True)
        raise
    print("ГОТОВО, однофайловый набор:", output)

def main():
    parser = argparse.ArgumentParser(description="Portable Telegram Archive (no Docker)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare", help="На Windows собери переносимую папку")
    p.add_argument("--export", required=True, help="Каталог с result.json и всеми медиа")
    p.add_argument("--bundle", required=True, help="Папка готового набора")
    p.add_argument("--export-name", default="first-export", help="Имя новой папки под exports/")
    p.add_argument("--copy-export", action="store_true", help="КОПИРОВАТЬ экспорт, если он лежит отдельно (нужно столько же места)")
    p.add_argument("--expect-chat-records", type=int, default=0,
                   help="Ожидаемое точное число записей chats.list + left_chats.list из отчёта")
    p.add_argument("--expect-message-records", type=int, default=0,
                   help="Ожидаемое точное число сообщений из отчёта")
    v = sub.add_parser("verify", help="Проверить переносимый набор до/после передачи")
    v.add_argument("--bundle", required=True)
    v.add_argument("--full", action="store_true", help="Проверить наличие всех медиа (медленно)")
    a = sub.add_parser("activate", help="Привязать SQLite к путям Linux после загрузки")
    a.add_argument("--bundle", required=True)
    tar_cmd = sub.add_parser("pack", help="Необязательно: записать весь готовый набор в один .tar")
    tar_cmd.add_argument("--bundle", required=True)
    tar_cmd.add_argument("--output", required=True, help="Путь вне bundle; нужно место размером с весь набор")
    pw = sub.add_parser("preflight-password", help="Проверить/установить пароль ДО перемещения экспорта")
    pw.add_argument("--bundle", required=True)
    pw.add_argument("--gui", action="store_true", help="Окна с поддержкой Ctrl+V (Windows)")
    rp = sub.add_parser("reset-password", help="Сменить пароль без повторного импорта")
    rp.add_argument("--bundle", required=True)
    rp.add_argument("--gui", action="store_true")
    args = parser.parse_args()
    if args.cmd == "preflight-password":
        preflight_password(canonical(args.bundle), args.gui)
    elif args.cmd == "reset-password":
        reset_password(canonical(args.bundle), args.gui)
    elif args.cmd == "prepare":
        if not args.export_name or args.export_name in (".", "..") or "/" in args.export_name or "\\" in args.export_name:
            fail("Имя экспорта должно быть простым именем папки.")
        prepare(args)
    elif args.cmd == "verify":
        verify(canonical(args.bundle), args.full)
    elif args.cmd == "pack":
        pack(canonical(args.bundle), Path(args.output))
    else:
        activate(canonical(args.bundle))


if __name__ == "__main__":
    main()
