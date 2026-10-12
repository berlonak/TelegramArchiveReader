# copyright by berlonak
# telegram: @Kilax123
"""Synthetic fixtures modelled on the Telegram Desktop JSON export field layout.
No actual personal chat texts, paths or identities are embedded in these tests.
"""
import json
import os
import sqlite3
from pathlib import Path
from types import SimpleNamespace

from tgarchive.db import connect
from tgarchive.importer import import_export
from bundletool import file_inventory


def test_combined_html_json_and_left_chats(tmp_path, monkeypatch):
    monkeypatch.setenv("TGARCHIVE_DATA_DIR", str(tmp_path / "db"))
    source = tmp_path / "export"
    source.mkdir()
    (source / "export_results.html").write_text("<!doctype html><title>Export</title>")
    (source / "lists").mkdir()
    (source / "lists" / "chats.html").write_text("<!doctype html><title>Chats</title>")
    (source / "chats" / "chat_0001" / "photos").mkdir(parents=True)
    (source / "chats" / "chat_0001" / "photos" / "one.jpg").write_bytes(b"photo")
    obj = {
        "personal_information": {"user_id": 10, "first_name": "Demo", "phone_number": "not indexed"},
        "chats": {"list": [
            {"id": 1, "name": None, "type": "private_supergroup", "messages": [
                {"id": 1, "date_unixtime": "1690000000", "text": "", "photo": "chats/chat_0001/photos/one.jpg"},
                {"id": 2, "date_unixtime": "1690000001", "text": "", "poll": {"question": ["Test ", {"type": "bold", "text": "poll"}], "answers": []}},
                {"id": 3, "date_unixtime": "1690000002", "text": "", "sticker_emoji": "⭐", "file": "not-included.tgs"},
            ]},
            {"id": 2, "name": "Sample channel", "type": "public_channel", "messages": []},
        ]},
        "left_chats": {"list": [
            {"id": 3, "name": "Old chat", "type": "private_supergroup", "messages": [
                {"id": 4, "date_unixtime": "1680000000", "text": "archive entry", "reply_to_peer_id": "peer-1"}
            ]}
        ]},
        "sessions": {"list": [{"last_ip": "not indexed"}]},
    }
    (source / "result.json").write_text(json.dumps(obj, ensure_ascii=False), encoding="utf8")
    audit = import_export(source, progress=False)
    assert (audit["chats"], audit["left_chats"], audit["messages"]) == (3, 1, 4)
    assert (audit["media_references"], audit["media_present"], audit["media_missing"]) == (2, 1, 1)
    with connect() as conn:
        left = conn.execute("SELECT title,left_archive FROM chats WHERE telegram_id='3'").fetchone()
        assert dict(left) == {"title": "Old chat", "left_archive": 1}
        assert conn.execute("SELECT title FROM chats WHERE telegram_id='1'").fetchone()[0] == "Без названия"
        assert conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 4
        assert conn.execute("SELECT body FROM messages WHERE tg_id='2'").fetchone()[0] == "Опрос: Test poll"
        assert conn.execute("SELECT body FROM messages WHERE tg_id='3'").fetchone()[0] == "⭐"
        assert conn.execute("SELECT COUNT(*) FROM media").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM messages_fts WHERE messages_fts MATCH 'poll'").fetchone()[0] == 1
        # No account sessions should be indexed as chat content.
        assert "last_ip" not in {x[0] for x in conn.execute("SELECT name FROM config")}
    inventory = file_inventory(source)
    assert inventory["file_count"] == 4
    assert inventory["total_bytes"] > len((source / "result.json").read_bytes())
