# copyright by berlonak
# telegram: @Kilax123
"""No-Docker administration: init, import, serve, stats, reindex FTS, change password."""
from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import sys
import time
from .app import PASS_HASHER
from .db import connect, data_dir, get_config, initialize, set_config
from .importer import import_export


def set_password() -> None:
    password = getpass.getpass("Новый пароль (не менее 12 символов): ")
    again = getpass.getpass("Повторите пароль: ")
    if len(password) < 12:
        sys.exit("Ошибка: пароль должен содержать минимум 12 символов.")
    if password != again:
        sys.exit("Ошибка: пароли не совпали.")
    with connect() as conn:
        initialize(conn)
        set_config(conn, "password_hash", PASS_HASHER.hash(password))
        conn.execute("DELETE FROM sessions")
        conn.commit()
    print("Пароль сохранен (Argon2id), старые сессии сброшены.")


def main():
    parser = argparse.ArgumentParser(description="Telegram Archive — личный архив Telegram Desktop JSON")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="Первичная настройка и пароль")
    sub.add_parser("change-password", help="Сменить пароль и завершить все сессии")
    importer = sub.add_parser("import", help="Импортировать полный экспорт или отдельный чат")
    importer.add_argument("path", help="Путь к каталогу с result.json или самому файлу")
    serve = sub.add_parser("serve", help="Запустить веб-сервер (только localhost)")
    serve.add_argument("--port", type=int, default=8000)
    sub.add_parser("stats", help="Статистика базы данных")
    sub.add_parser("reindex", help="Восстановить поисковый индекс FTS5")
    args = parser.parse_args()
    if args.command in ("init", "change-password"):
        if args.command == "init":
            print("Каталог данных:", data_dir())
        set_password()
    elif args.command == "import":
        print("Читаю JSON без изменения оригинальных файлов...")
        result = import_export(args.path)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("Важно: сохраняйте оригинальный каталог экспорта по этому пути: медиа берутся из него.")
    elif args.command == "serve":
        import uvicorn
        with connect() as conn:
            initialize(conn)
            if not get_config(conn, "password_hash"):
                sys.exit("Сначала задайте пароль: tgarchive init")
        # Never bind to public interfaces; nginx is the only public entry point.
        uvicorn.run("tgarchive.app:app", host="127.0.0.1", port=args.port, proxy_headers=False, workers=1)
    elif args.command == "stats":
        with connect() as conn:
            initialize(conn)
            n = conn.execute("SELECT COUNT(*) chats, COALESCE(SUM(messages_count),0) messages FROM chats").fetchone()
            media = conn.execute("SELECT COUNT(*) total FROM media").fetchone()
            print(f"Чатов: {n['chats']:,}; сообщений: {n['messages']:,}; медиа: {media['total']:,}")
    elif args.command == "reindex":
        with connect() as conn:
            initialize(conn)
            conn.execute("INSERT INTO messages_fts(messages_fts) VALUES ('rebuild')")
            conn.commit()
            print("Поисковый индекс восстановлен.")


if __name__ == "__main__":
    main()
