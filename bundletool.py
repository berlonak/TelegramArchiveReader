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
try:
    from tgarchive.messages import msg
except ImportError:  # inside a ready bundle the package lives in app/
    sys.path.insert(0, str(ROOT / "app"))
    from tgarchive.messages import msg
TOKEN = "@TGARCHIVE_BUNDLE@/"
VERSION = 1


def fail(message: str) -> None:
    raise SystemExit(msg("error", message=message))


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
                fail(msg("bt.symlink_dir", path=where / name))
        for name in files:
            path = where / name
            if path.is_symlink() or not path.is_file():
                fail(msg("bt.special_file", path=path))
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
    for guide in ("SERVER.md", "SERVER-RU.md"):
        shutil.copy2(ROOT / guide, bundle / guide)
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
        fail(msg("bt.no_tk"))
    root = tk.Tk()
    root.withdraw()
    try:
        for _ in range(3):
            password = simpledialog.askstring(
                msg("bt.dlg_title"), msg("bt.dlg_prompt"),
                show="*", parent=root,
            )
            if password is None:
                fail(msg("bt.dlg_cancelled"))
            if len(password) < 12:
                messagebox.showerror(msg("bt.dlg_error_title"), msg("bt.dlg_too_short"), parent=root)
                continue
            if not confirm:
                return password
            again = simpledialog.askstring(
                msg("bt.dlg_confirm_title"), msg("bt.dlg_confirm"),
                show="*", parent=root,
            )
            if again is None:
                fail(msg("bt.dlg_cancelled"))
            if password == again:
                return password
            messagebox.showerror(msg("bt.dlg_error_title"), msg("bt.dlg_mismatch"), parent=root)
        fail(msg("bt.dlg_three_tries"))
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
            fail(msg("bt.partial_db_ready"))
        # No original data has been imported yet; a password-only stub from a
        # failed Move-Item attempt is safe to replace after new confirmation.
        if gui:
            password = prompt_password_gui(True)
        else:
            password = getpass.getpass(msg("password_prompt"))
            again = getpass.getpass(msg("password_repeat"))
            if len(password) < 12 or password != again:
                fail(msg("bt.preflight_bad"))
        password_hash = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2).hash(password)
        conn.execute("INSERT OR REPLACE INTO config(name,value) VALUES('password_hash',?)", (password_hash,))
        conn.commit()
    print(msg("bt.preflight_ok"))


def reset_password(bundle: Path, gui: bool) -> None:
    """Change password in a completed bundle without touching media or reimporting."""
    from argon2 import PasswordHasher
    db = bundle / "data" / "archive.sqlite3"
    if not db.is_file():
        fail(msg("bt.reset_no_db"))
    print(msg("bt.reset_stop_first"))
    if gui:
        password = prompt_password_gui(True)
    else:
        password = getpass.getpass(msg("password_new"))
        again = getpass.getpass(msg("password_repeat"))
        if password != again or len(password) < 12:
            fail(msg("bt.reset_bad"))
    digest = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2).hash(password)
    conn = sqlite3.connect(db, timeout=2)
    try:
        conn.execute("PRAGMA busy_timeout=2000")
        conn.execute("BEGIN IMMEDIATE")
        if not conn.execute("SELECT 1 FROM config WHERE name='password_hash'").fetchone():
            fail(msg("bt.reset_no_password"))
        conn.execute("UPDATE config SET value=? WHERE name='password_hash'", (digest,))
        conn.execute("DELETE FROM sessions")
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()
    print(msg("bt.reset_ok"))


def ask_password(db_file: Path) -> None:
    from argon2 import PasswordHasher
    from tgarchive.db import get_config, initialize
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    initialize(conn)
    if get_config(conn, "password_hash"):
        print(msg("bt.password_exists"))
        conn.close()
        return
    password = getpass.getpass(msg("bt.archive_password"))
    again = getpass.getpass(msg("password_repeat"))
    if len(password) < 12 or password != again:
        conn.close()
        fail(msg("bt.password_bad"))
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
            fail(msg("bt.import_outside", id=row["id"], root=root))
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
        fail(msg("bt.no_result_json", root=root))
    return source


def prepare(args: argparse.Namespace) -> None:
    try:
        import ijson  # noqa: F401 - demand streaming parser for large histories
        import fastapi  # noqa: F401
        import argon2  # noqa: F401
    except ImportError:
        fail(msg("bt.install_deps"))
    from tgarchive.importer import import_export, import_contacts_only
    bundle = canonical(args.bundle)
    export = canonical(args.export)
    if not export.is_dir():
        fail(msg("bt.no_export_dir", path=export))
    ensure_json(export)
    if in_tree(bundle, export):
        fail(msg("bt.bundle_inside_export"))
    bundle.mkdir(parents=True, exist_ok=True)
    exports = bundle / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    dest = exports / args.export_name
    if not in_tree(export, exports):
        if not args.copy_export:
            fail(msg("bt.export_outside"))
        if dest.exists():
            fail(msg("bt.dest_exists", path=dest))
        if in_tree(bundle, export):
            fail(msg("bt.copy_into_self"))
        print(msg("bt.copying"))
        shutil.copytree(export, dest, symlinks=False)
        export = dest
    else:
        if not export.parent == exports:
            fail(msg("bt.export_not_direct"))
    print(msg("bt.source", path=export))
    combined = (export / "export_results.html").is_file()
    print(msg("bt.structure", kind=msg("bt.structure_combined") if combined else "JSON"))
    print(msg("bt.inventory"))
    inventory = file_inventory(export)
    print(msg("bt.inventory_result", count=inventory["file_count"], size=inventory["total_bytes"]))
    copy_application(bundle)
    manifest_path = bundle / "bundle-manifest.json"
    if manifest_path.exists():
        fail(msg("bt.manifest_exists"))
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
                fail(msg("bt.partial_db"))
            if not get_config(check, "password_hash"):
                fail(msg("bt.db_no_password"))
    os.environ["TGARCHIVE_DATA_DIR"] = str(data)
    ask_password(db_file)
    print(msg("bt.indexing"))
    try:
        result = import_export(export, progress=True)
        if getattr(args, "expect_chat_records", 0) and result["chats"] != args.expect_chat_records:
            fail(msg("bt.expect_chats", expected=args.expect_chat_records, actual=result["chats"]))
        if getattr(args, "expect_message_records", 0) and result["messages"] != args.expect_message_records:
            fail(msg("bt.expect_messages", expected=args.expect_message_records, actual=result["messages"]))
        print(msg("bt.indexing_contacts"))
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
            "app_version": "0.5.0", "contacts_indexed_count": contacts_count,
            "original_export_is_unchanged": True,
        }
        temporary = manifest_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(manifest_path)
        print(msg("bt.done"))
        print(msg("bt.done_stats", chats=stats["chats"], messages=stats["messages"], media=stats["media"]))
        print(msg("bt.done_chats", chats=result["chats"], left=result["left_chats"]))
        print(msg("bt.done_media", refs=result["media_references"], present=result["media_present"],
                  missing=result["media_missing"]))
        if result["media_missing"]:
            print(msg("bt.media_missing"))
        print(msg("bt.folder", path=bundle))
    except BaseException:
        print(msg("bt.build_failed"), file=sys.stderr)
        raise


def read_manifest(bundle: Path) -> dict:
    path = bundle / "bundle-manifest.json"
    if not path.is_file():
        fail(msg("bt.no_manifest"))
    meta = json.loads(path.read_text(encoding="utf-8"))
    if meta.get("format") != "telegram-archive-portable" or meta.get("format_version") != VERSION:
        fail(msg("bt.unknown_version"))
    return meta


def verify(bundle: Path, full: bool) -> None:
    meta = read_manifest(bundle)
    export_rel = Path(meta["primary_export"])
    if export_rel.is_absolute() or ".." in export_rel.parts or export_rel.parts[0] != "exports":
        fail(msg("bt.bad_manifest_path"))
    source = bundle / export_rel / "result.json"
    ensure_json(source.parent)
    print(msg("bt.sha_checking"))
    if sha256(source) != meta["telegram_json_sha256"]:
        fail(msg("bt.sha_mismatch"))
    if meta.get("source_inventory"):
        print(msg("bt.inventory_checking"))
        actual_inventory = file_inventory(source.parent)
        if actual_inventory != meta["source_inventory"]:
            fail(msg("bt.inventory_mismatch", expected=meta["source_inventory"], actual=actual_inventory))
    db_file = bundle / "data" / "archive.sqlite3"
    conn = sqlite3.connect(f"file:{db_file.as_posix()}?mode=ro", uri=True)
    qc = conn.execute("PRAGMA quick_check").fetchone()[0]
    if qc != "ok":
        fail(msg("bt.sqlite_error", error=qc))
    roots = {}
    for id_, raw in conn.execute("SELECT id,root FROM imports"):
        if raw.startswith(TOKEN):
            rel = Path(raw[len(TOKEN):])
            if rel.is_absolute() or ".." in rel.parts or rel.parts[0] != "exports":
                fail(msg("bt.bad_portable_ref"))
            roots[id_] = bundle / rel
        else:
            root = canonical(raw)
            if not in_tree(root, bundle / "exports"):
                fail(msg("bt.import_outside_bundle", root=root))
            roots[id_] = root
    for root in roots.values():
        ensure_json(root)
    if full:
        print(msg("bt.media_checking"))
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
            fail(msg("bt.media_not_found", examples="; ".join(missing)))
        print(msg("bt.media_seen", count=f"{seen:,}"))
    else:
        missing = []
        for import_id, relpath in conn.execute("SELECT import_id,relpath FROM media LIMIT 100"):
            root = roots[import_id]
            target = canonical(root / relpath)
            if not in_tree(target, canonical(root)) or not target.is_file():
                missing.append(str(target))
        if missing:
            fail(msg("bt.media_first100", examples="; ".join(missing[:4])))
    conn.close()
    print(msg("bt.verified"))


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
                    fail(msg("bt.suspicious_ref", ref=raw))
                root = canonical(bundle / rel)
                if not in_tree(root, bundle / "exports"):
                    fail(msg("bt.export_escapes", path=root))
                ensure_json(root)
                conn.execute("UPDATE imports SET root=?,source_file=? WHERE id=?",
                             (str(root), str(root / "result.json"), row["id"]))
            elif not in_tree(canonical(raw), bundle / "exports"):
                fail(msg("bt.unexpected_ref", ref=raw))
        conn.execute("DELETE FROM sessions")
        conn.commit()
        print(msg("bt.activated"))
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
        fail(msg("bt.tar_inside"))
    if output.exists():
        fail(msg("bt.file_exists", path=output))
    output.parent.mkdir(parents=True, exist_ok=True)
    print(msg("bt.packing"))
    try:
        with tarfile.open(output, mode="w|") as archive:
            archive.add(bundle, arcname="tgarchive", recursive=True)
    except BaseException:
        output.unlink(missing_ok=True)
        raise
    print(msg("bt.packed", path=output))

def main():
    parser = argparse.ArgumentParser(description=msg("bt.help"))
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare", help=msg("bt.help_prepare"))
    p.add_argument("--export", required=True, help=msg("bt.help_export"))
    p.add_argument("--bundle", required=True, help=msg("bt.help_bundle"))
    p.add_argument("--export-name", default="first-export", help=msg("bt.help_export_name"))
    p.add_argument("--copy-export", action="store_true", help=msg("bt.help_copy"))
    p.add_argument("--expect-chat-records", type=int, default=0,
                   help=msg("bt.help_expect_chats"))
    p.add_argument("--expect-message-records", type=int, default=0,
                   help=msg("bt.help_expect_messages"))
    v = sub.add_parser("verify", help=msg("bt.help_verify"))
    v.add_argument("--bundle", required=True)
    v.add_argument("--full", action="store_true", help=msg("bt.help_full"))
    a = sub.add_parser("activate", help=msg("bt.help_activate"))
    a.add_argument("--bundle", required=True)
    tar_cmd = sub.add_parser("pack", help=msg("bt.help_pack"))
    tar_cmd.add_argument("--bundle", required=True)
    tar_cmd.add_argument("--output", required=True, help=msg("bt.help_output"))
    pw = sub.add_parser("preflight-password", help=msg("bt.help_preflight"))
    pw.add_argument("--bundle", required=True)
    pw.add_argument("--gui", action="store_true", help=msg("bt.help_gui"))
    rp = sub.add_parser("reset-password", help=msg("bt.help_reset"))
    rp.add_argument("--bundle", required=True)
    rp.add_argument("--gui", action="store_true")
    args = parser.parse_args()
    if args.cmd == "preflight-password":
        preflight_password(canonical(args.bundle), args.gui)
    elif args.cmd == "reset-password":
        reset_password(canonical(args.bundle), args.gui)
    elif args.cmd == "prepare":
        if not args.export_name or args.export_name in (".", "..") or "/" in args.export_name or "\\" in args.export_name:
            fail(msg("bt.bad_export_name"))
        prepare(args)
    elif args.cmd == "verify":
        verify(canonical(args.bundle), args.full)
    elif args.cmd == "pack":
        pack(canonical(args.bundle), Path(args.output))
    else:
        activate(canonical(args.bundle))


if __name__ == "__main__":
    main()
