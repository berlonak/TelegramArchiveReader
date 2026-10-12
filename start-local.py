#!/usr/bin/env python3
# copyright by berlonak
# telegram: @Kilax123
"""Run a ready Telegram Archive bundle locally WITHOUT changing the portable paths in SQLite.

This file and START-LOCAL.bat are placed in the ROOT of TelegramArchive-ready.
Do not run bundletool activate locally: it writes absolute Windows paths and makes
a later move of the same bundle to Linux harder.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

BUNDLE = Path(__file__).resolve().parent
TOKEN = "@TGARCHIVE_BUNDLE@/"
sys.path.insert(0, str(BUNDLE / "app"))
from tgarchive.messages import msg  # noqa: E402 - needs the bundled app on sys.path


def preflight() -> None:
    required = [
        BUNDLE / "bundle-manifest.json", BUNDLE / "data" / "archive.sqlite3",
        BUNDLE / "app" / "tgarchive" / "app.py", BUNDLE / "exports",
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise RuntimeError(msg("local.incomplete", missing="\n".join(missing)))
    meta = json.loads((BUNDLE / "bundle-manifest.json").read_text(encoding="utf-8"))
    if meta.get("format") != "telegram-archive-portable":
        raise RuntimeError(msg("local.not_bundle"))
    if not (BUNDLE / meta["primary_export"] / "result.json").is_file():
        raise RuntimeError(msg("local.no_json"))


def main() -> None:
    preflight()
    # The SQLite index stays inside the bundle; the virtual environment lives OUTSIDE it.
    os.environ["TGARCHIVE_DATA_DIR"] = str((BUNDLE / "data").resolve())
    os.environ["TGARCHIVE_BUNDLE_ROOT"] = str(BUNDLE.resolve())
    os.environ["TGARCHIVE_HTTPS"] = "0"  # Loopback only, NOT for internet access.

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
            raise RuntimeError(msg("local.no_password"))

    print("\n" + msg("local.summary", chats=f"{chats:,}", messages=f"{messages:,}"))
    print(msg("local.open"))
    print(msg("local.password_hint"))
    print(msg("local.stop_hint") + "\n")

    try:
        uvicorn.run(site.app, host="127.0.0.1", port=8000, workers=1, proxy_headers=False)
    finally:
        # Checkpoint on shutdown so a later transfer never copies a live WAL file.
        db = BUNDLE / "data" / "archive.sqlite3"
        with sqlite3.connect(db, timeout=10) as conn:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n" + msg("local.stopped"))
    except Exception as exc:
        print("\n" + msg("error", message=exc), file=sys.stderr)
        raise SystemExit(1)
