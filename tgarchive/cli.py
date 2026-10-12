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
from .messages import msg


def set_password() -> None:
    password = getpass.getpass(msg("password_new"))
    again = getpass.getpass(msg("password_repeat"))
    if len(password) < 12:
        sys.exit(msg("error", message=msg("cli.too_short")))
    if password != again:
        sys.exit(msg("error", message=msg("cli.mismatch")))
    with connect() as conn:
        initialize(conn)
        set_config(conn, "password_hash", PASS_HASHER.hash(password))
        conn.execute("DELETE FROM sessions")
        conn.commit()
    print(msg("cli.saved"))


def main():
    parser = argparse.ArgumentParser(description=msg("cli.description"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help=msg("cli.init"))
    sub.add_parser("change-password", help=msg("cli.change_password"))
    importer = sub.add_parser("import", help=msg("cli.import"))
    importer.add_argument("path", help=msg("cli.import_path"))
    serve = sub.add_parser("serve", help=msg("cli.serve"))
    serve.add_argument("--port", type=int, default=8000, help=msg("cli.port"))
    sub.add_parser("stats", help=msg("cli.stats"))
    sub.add_parser("reindex", help=msg("cli.reindex"))
    args = parser.parse_args()
    if args.command in ("init", "change-password"):
        if args.command == "init":
            print(msg("cli.data_dir", path=data_dir()))
        set_password()
    elif args.command == "import":
        print(msg("cli.reading"))
        result = import_export(args.path)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print(msg("cli.keep_export"))
    elif args.command == "serve":
        import uvicorn
        with connect() as conn:
            initialize(conn)
            if not get_config(conn, "password_hash"):
                sys.exit(msg("cli.need_password"))
        # Never bind to public interfaces; nginx is the only public entry point.
        uvicorn.run("tgarchive.app:app", host="127.0.0.1", port=args.port, proxy_headers=False, workers=1)
    elif args.command == "stats":
        with connect() as conn:
            initialize(conn)
            n = conn.execute("SELECT COUNT(*) chats, COALESCE(SUM(messages_count),0) messages FROM chats").fetchone()
            media = conn.execute("SELECT COUNT(*) total FROM media").fetchone()
            print(msg("cli.stats_line", chats=f"{n['chats']:,}", messages=f"{n['messages']:,}", media=f"{media['total']:,}"))
    elif args.command == "reindex":
        with connect() as conn:
            initialize(conn)
            conn.execute("INSERT INTO messages_fts(messages_fts) VALUES ('rebuild')")
            conn.commit()
            print(msg("cli.reindexed"))


if __name__ == "__main__":
    main()
