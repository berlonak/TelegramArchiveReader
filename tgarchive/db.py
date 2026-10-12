# copyright by berlonak
# telegram: @Kilax123
"""SQLite schema, connections and FTS index. All original export files remain untouched."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path


def data_dir() -> Path:
    return Path(os.environ.get("TGARCHIVE_DATA_DIR", "./archive-data")).expanduser().resolve()


def db_path() -> Path:
    return data_dir() / "archive.sqlite3"


def connect() -> sqlite3.Connection:
    root = data_dir()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    conn = sqlite3.connect(db_path(), timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS config (
    name TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY,
    import_id INTEGER NOT NULL REFERENCES imports(id) ON DELETE CASCADE,
    telegram_user_id TEXT,
    first_name TEXT NOT NULL DEFAULT '',
    last_name TEXT NOT NULL DEFAULT '',
    phone_number TEXT NOT NULL DEFAULT '',
    exported_at TEXT NOT NULL DEFAULT '',
    UNIQUE(import_id, telegram_user_id, first_name, last_name, phone_number)
);
CREATE INDEX IF NOT EXISTS contacts_name_idx ON contacts(first_name,last_name);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    expires_at INTEGER NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS imports (
    id INTEGER PRIMARY KEY,
    root TEXT NOT NULL,
    source_file TEXT NOT NULL,
    imported_at INTEGER NOT NULL,
    messages_seen INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS chats (
    id INTEGER PRIMARY KEY,
    chat_key TEXT UNIQUE NOT NULL,
    telegram_id TEXT,
    title TEXT NOT NULL,
    kind TEXT NOT NULL,
    category TEXT NOT NULL,
    left_archive INTEGER NOT NULL DEFAULT 0,
    messages_count INTEGER NOT NULL DEFAULT 0,
    last_ts INTEGER NOT NULL DEFAULT 0,
    last_preview TEXT NOT NULL DEFAULT '',
    avatar_import_id INTEGER REFERENCES imports(id),
    avatar_path TEXT
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY,
    chat_id INTEGER NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    tg_id TEXT NOT NULL,
    ts INTEGER NOT NULL,
    date_iso TEXT NOT NULL,
    sender TEXT NOT NULL DEFAULT '',
    sender_id TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL DEFAULT '',
    search_text TEXT NOT NULL DEFAULT '',
    entities_json TEXT NOT NULL DEFAULT '[]',
    type TEXT NOT NULL DEFAULT 'message',
    action TEXT NOT NULL DEFAULT '',
    reply_to TEXT,
    forwarded_from TEXT,
    edited TEXT,
    album_id TEXT,
    reactions_json TEXT NOT NULL DEFAULT '[]',
    extra_json TEXT NOT NULL DEFAULT '{}',
    UNIQUE(chat_id, tg_id)
);
CREATE INDEX IF NOT EXISTS messages_chat_time_idx ON messages(chat_id, ts, id);
CREATE INDEX IF NOT EXISTS messages_sender_idx ON messages(sender);
CREATE TABLE IF NOT EXISTS media (
    id INTEGER PRIMARY KEY,
    message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    import_id INTEGER NOT NULL REFERENCES imports(id) ON DELETE CASCADE,
    relpath TEXT NOT NULL,
    kind TEXT NOT NULL,
    filename TEXT NOT NULL,
    mime TEXT NOT NULL DEFAULT '',
    width INTEGER,
    height INTEGER,
    file_size INTEGER,
    UNIQUE(message_id, kind, relpath)
);
CREATE INDEX IF NOT EXISTS media_message_idx ON media(message_id);
CREATE INDEX IF NOT EXISTS media_kind_idx ON media(kind, id);
CREATE TABLE IF NOT EXISTS bookmarks (
    message_id INTEGER PRIMARY KEY REFERENCES messages(id) ON DELETE CASCADE,
    created_at INTEGER NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    search_text, sender, content='messages', content_rowid='id',
    tokenize='unicode61 remove_diacritics 2', prefix='2 3 4'
);
CREATE TRIGGER IF NOT EXISTS msg_fts_insert AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, search_text, sender)
    VALUES(new.id, new.search_text, new.sender);
END;
CREATE TRIGGER IF NOT EXISTS msg_fts_delete AFTER DELETE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, search_text, sender)
    VALUES('delete', old.id, old.search_text, old.sender);
END;
CREATE TRIGGER IF NOT EXISTS msg_fts_update AFTER UPDATE OF search_text, sender ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, search_text, sender)
    VALUES('delete', old.id, old.search_text, old.sender);
    INSERT INTO messages_fts(rowid, search_text, sender)
    VALUES(new.id, new.search_text, new.sender);
END;
"""


def initialize(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    # Allow opening an existing v0.1 database with the additional archived-chat label.
    columns = {row[1] for row in conn.execute("PRAGMA table_info(chats)")}
    if "left_archive" not in columns:
        conn.execute("ALTER TABLE chats ADD COLUMN left_archive INTEGER NOT NULL DEFAULT 0")
    conn.commit()


def get_config(conn: sqlite3.Connection, name: str, default: str = "") -> str:
    row = conn.execute("SELECT value FROM config WHERE name = ?", (name,)).fetchone()
    return row["value"] if row else default


def set_config(conn: sqlite3.Connection, name: str, value: str) -> None:
    conn.execute("INSERT INTO config(name,value) VALUES(?,?) ON CONFLICT(name) DO UPDATE SET value=excluded.value", (name, value))
