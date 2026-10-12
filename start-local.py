#!/usr/bin/env python3
# copyright by berlonak
# telegram: @Kilax123
"""Запустить замороженный Telegram Archive локально, НЕ меняя переносимые пути в SQLite.

Этот файл и START-LOCAL.bat кладутся в КОРЕНЬ TelegramArchive-ready.
Не выполняйте bundletool activate локально: он записывает абсолютные пути Windows
и усложняет последующий перенос этого же пакета на Linux.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

BUNDLE = Path(__file__).resolve().parent
TOKEN = "@TGARCHIVE_BUNDLE@/"


def preflight() -> None:
    required = [
        BUNDLE / "bundle-manifest.json", BUNDLE / "data" / "archive.sqlite3",
        BUNDLE / "app" / "tgarchive" / "app.py", BUNDLE / "exports",
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise RuntimeError("Неполный готовый архив. Отсутствует:\n" + "\n".join(missing))
    meta = json.loads((BUNDLE / "bundle-manifest.json").read_text(encoding="utf-8"))
    if meta.get("format") != "telegram-archive-portable":
        raise RuntimeError("Это не переносимый архив Telegram Archive.")
    if not (BUNDLE / meta["primary_export"] / "result.json").is_file():
        raise RuntimeError("Исходный result.json не найден в готовой папке.")


def main() -> None:
    preflight()
    # SQLite индекс остаётся в готовом пакете; виртуальное окружение лежит СНАРУЖИ.
    os.environ["TGARCHIVE_DATA_DIR"] = str((BUNDLE / "data").resolve())
    os.environ["TGARCHIVE_BUNDLE_ROOT"] = str(BUNDLE.resolve())
    os.environ["TGARCHIVE_HTTPS"] = "0"  # Только loopback, НЕ для подключения из интернета.
    sys.path.insert(0, str(BUNDLE / "app"))

    import importlib
    import uvicorn
    from tgarchive.db import connect
    site = importlib.import_module("tgarchive.app")
    # v0.3 resolves portable paths natively via TGARCHIVE_BUNDLE_ROOT.

    with connect() as conn:
        chats = conn.execute("SELECT COUNT(*) FROM chats").fetchone()[0]
        messages = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        password = conn.execute("SELECT value FROM config WHERE name='password_hash'").fetchone()
        if not password:
            raise RuntimeError("В базе нет пароля. Проверь полноту готового пакета.")

    print(f"\nTelegram Archive: {chats:,} чатов; {messages:,} сообщений.")
    print("ОТКРОЙ: http://127.0.0.1:8000")
    print("Вводи пароль, который задавал при подготовке архива.")
    print("Для остановки нажми Ctrl+C в этом окне. Не открывай порт 8000 наружу.\n")

    try:
        uvicorn.run(site.app, host="127.0.0.1", port=8000, workers=1, proxy_headers=False)
    finally:
        # Дождаться остановки, чтобы при будущем переносе не скопировать живой WAL.
        db = BUNDLE / "data" / "archive.sqlite3"
        with sqlite3.connect(db, timeout=10) as conn:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nОстановлено.")
    except Exception as exc:
        print(f"\nОшибка: {exc}", file=sys.stderr)
        raise SystemExit(1)
