# copyright by berlonak
# telegram: @Kilax123
"""Incremental JSON import. Streams with ijson so large full-account exports needn't fit in RAM."""
from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .db import connect, get_config, initialize, set_config
from .messages import msg

try:
    import ijson
except ImportError:  # limited fallback for small fixtures / no ijson installation
    ijson = None


MEDIA_FIELDS = ("photo", "file", "thumbnail", "contact_vcard")


def extract_text(value: Any) -> tuple[str, list[dict]]:
    """Telegram text may be a string or mixed rich-text element list."""
    if isinstance(value, str):
        return value, ([{"type": "plain", "text": value}] if value else [])
    if isinstance(value, list):
        segments: list[dict] = []
        for item in value:
            if isinstance(item, str):
                segments.append({"type": "plain", "text": item})
            elif isinstance(item, dict):
                segments.append({"type": str(item.get("type", "plain")), "text": str(item.get("text") or ""),
                                 "href": str(item.get("href") or "")})
        return "".join(x["text"] for x in segments), segments
    return "", []


def parse_time(message: dict) -> tuple[int, str]:
    # date_unixtime is present on newer Desktop exports; dates without tz are local export times.
    raw = message.get("date_unixtime")
    if raw is not None:
        try:
            ts = int(raw)
            return ts, datetime.fromtimestamp(ts, timezone.utc).isoformat()
        except (ValueError, TypeError, OverflowError):
            pass
    value = str(message.get("date") or "")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        # A naïve export time is interpreted as UTC for stable, reproducible ordering.
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return int(parsed.timestamp()), parsed.isoformat()
    except (ValueError, OverflowError):
        return 0, value


def classify_chat(kind: str, name: str) -> str:
    low = kind.lower()
    if "saved" in low or name.lower() in {"saved messages", "избранное"}:
        return "saved"
    if "channel" in low:
        return "channels"
    if "group" in low:
        return "groups"
    return "personal"


def valid_relative_path(raw: Any) -> str | None:
    """Reject absolute, drive, URL, traversal, NUL and Windows backslash surprises."""
    if not isinstance(raw, str) or not raw or "\x00" in raw:
        return None
    raw = raw.replace("\\", "/")  # Windows exports may use backslashes.
    if raw.startswith(("/", "~")) or re.match(r"^[A-Za-z]:", raw) or "://" in raw:
        return None
    p = Path(raw)
    if any(part in {"..", "."} for part in p.parts):
        return None
    return p.as_posix()


def classify_media(message: dict, field: str, relpath: str) -> str:
    media_type = str(message.get("media_type") or "").lower()
    if field == "photo":
        return "photo"
    if field == "thumbnail":
        return "thumbnail"
    if field == "contact_vcard":
        return "file"
    if "sticker" in media_type:
        return "sticker"
    if "video_message" in media_type or "round" in media_type:
        return "video_message"
    if "video" in media_type:
        return "video"
    if "voice" in media_type:
        return "voice"
    if "audio" in media_type:
        return "audio"
    if "animation" in media_type or "gif" in media_type:
        return "animation"
    suffix = Path(relpath).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".heic", ".avif"}:
        return "photo"
    if suffix in {".mp4", ".mov", ".webm", ".mkv"}:
        return "video"
    if suffix in {".ogg", ".oga", ".opus"}:
        return "voice"
    if suffix in {".mp3", ".flac", ".m4a", ".wav"}:
        return "audio"
    if suffix in {".gif", ".tgs"}:
        return "animation" if suffix == ".gif" else "sticker"
    return "file"


def media_from_message(m: dict) -> list[dict]:
    records: list[dict] = []
    for field in MEDIA_FIELDS:
        value = m.get(field)
        # Missing media sometimes appears as '(File not included. Change data exporting settings...)'
        if isinstance(value, dict):
            value = value.get("file") or value.get("path")
        path = valid_relative_path(value)
        if not path:
            continue
        kind = classify_media(m, field, path)
        records.append({
            "relpath": path, "kind": kind, "filename": str(m.get("file_name") or Path(path).name),
            "mime": str(m.get("mime_type") or mimetypes.guess_type(path)[0] or ""),
            "width": m.get("width") if isinstance(m.get("width"), int) else None,
            "height": m.get("height") if isinstance(m.get("height"), int) else None,
            "file_size": m.get("file_size") if isinstance(m.get("file_size"), int) else None,
        })
    return records


def stream_events(path: Path) -> Iterator[tuple[str, dict]]:
    """Yields ('start', metadata), ('message', raw), ('end', {}) per chat.

    Full-account exports: chats.list and left_chats.list; one-chat exports: root messages.
    The ijson parser builds only one message in memory at a time.
    """
    if ijson is None:
        with path.open("r", encoding="utf-8") as f:
            obj = json.load(f)
        profile = obj.get("personal_information")
        if isinstance(profile, dict):
            for field in ("user_id", "first_name", "last_name"):
                if profile.get(field) is not None:
                    yield "profile", {"key": field, "value": profile[field]}
        for group in (obj.get("chats", {}).get("list", []) if isinstance(obj.get("chats"), dict) else []):
            yield "start", {**{k: group.get(k) for k in ("id", "name", "type", "photo")}, "left_archive": False}
            for message in group.get("messages") or []:
                yield "message", message
            yield "end", {}
        left = obj.get("left_chats", {})
        for group in (left.get("list", []) if isinstance(left, dict) else []):
            yield "start", {**{k: group.get(k) for k in ("id", "name", "type", "photo")}, "left_archive": True}
            for message in group.get("messages") or []:
                yield "message", message
            yield "end", {}
        if "messages" in obj:
            yield "start", {k: obj.get(k) for k in ("id", "name", "type", "photo")}
            for message in obj.get("messages") or []:
                yield "message", message
            yield "end", {}
        return

    # Streaming parser: top-level account metadata, each chat's direct scalar metadata,
    # and each complete message value are handled without ever building whole chats.
    prefixes = ("chats.list.item", "left_chats.list.item")
    active: str | None = None
    metadata: dict[str, Any] = {}
    builder = None
    depth = 0
    root_meta: dict[str, Any] = {}
    root_started = False
    with path.open("rb") as file:
        for prefix, event, value in ijson.parse(file):
            if builder is not None:
                builder.event(event, value)
                if event in ("start_map", "start_array"):
                    depth += 1
                elif event in ("end_map", "end_array"):
                    depth -= 1
                    if depth == 0:
                        yield "message", builder.value
                        builder = None
                continue
            if prefix in prefixes and event == "start_map":
                active, metadata = prefix, {"left_archive": prefix.startswith("left_chats.")}
                continue
            if active and prefix == active + ".messages.item" and event in ("start_map", "start_array"):
                if not metadata.get("_started"):
                    metadata["_started"] = True
                    yield "start", {k: v for k, v in metadata.items() if not k.startswith("_")}
                builder = ijson.common.ObjectBuilder()
                builder.event(event, value)
                depth = 1
                continue
            if active and prefix == active and event == "end_map":
                if not metadata.get("_started"):
                    yield "start", metadata
                yield "end", {}
                active, metadata = None, {}
                continue
            if active and prefix.startswith(active + "."):
                field = prefix[len(active) + 1:]
                if field in {"id", "name", "type", "photo"} and event in ("string", "number", "null"):
                    metadata[field] = value
                continue
            if prefix == "messages.item" and event in ("start_map", "start_array"):
                if not root_started:
                    root_started = True
                    yield "start", root_meta
                builder = ijson.common.ObjectBuilder()
                builder.event(event, value)
                depth = 1
                continue
            if prefix in {"personal_information.user_id", "personal_information.first_name", "personal_information.last_name"} and event in ("string", "number"):
                yield "profile", {"key": prefix.rsplit(".", 1)[-1], "value": value}
            if prefix in {"id", "name", "type", "photo"} and event in ("string", "number", "null"):
                root_meta[prefix] = value
            if prefix == "messages" and event == "end_array":
                if not root_started:
                    yield "start", root_meta
                yield "end", {}
                root_started = False


def chat_key(meta: dict) -> str:
    kind = str(meta.get("type") or "unknown")
    tid = meta.get("id")
    if tid is not None and tid != "":
        return f"{kind}:{tid}"
    # Only used for malformed/export variants without IDs; collision risk if titles repeat.
    return "unnumbered:" + hashlib.sha256(f"{kind}:{meta.get('name','')}".encode()).hexdigest()[:24]


def ensure_chat(conn: sqlite3.Connection, meta: dict, import_id: int, root: Path) -> int:
    key = chat_key(meta)
    title = str(meta.get("name") or (msg("import.saved_title") if "saved" in str(meta.get("type")) else msg("import.untitled")))
    kind = str(meta.get("type") or "unknown")
    avatar = valid_relative_path(meta.get("photo"))
    if avatar and not (root / avatar).resolve().is_relative_to(root):
        avatar = None
    conn.execute("""INSERT INTO chats(chat_key,telegram_id,title,kind,category,left_archive,avatar_import_id,avatar_path)
        VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(chat_key) DO UPDATE SET
        title=CASE WHEN excluded.left_archive=1 AND chats.left_archive=0
                   THEN chats.title ELSE excluded.title END,
        kind=excluded.kind,category=excluded.category,
        left_archive=chats.left_archive AND excluded.left_archive,
        avatar_import_id=COALESCE(excluded.avatar_import_id,chats.avatar_import_id),
        avatar_path=COALESCE(excluded.avatar_path,chats.avatar_path)""",
        (key, str(meta["id"]) if meta.get("id") is not None else None, title, kind,
         classify_chat(kind, title), int(bool(meta.get("left_archive"))),
         import_id if avatar else None, avatar))
    return conn.execute("SELECT id FROM chats WHERE chat_key=?", (key,)).fetchone()["id"]


def process_message(conn: sqlite3.Connection, m: dict, chat_id: int, import_id: int,
                    root: Path, audit: dict[str, int] | None = None) -> bool:
    tid = m.get("id")
    if tid is None:
        return False
    text, segments = extract_text(m.get("text"))
    if isinstance(m.get("text_entities"), list):
        provided = m["text_entities"]
        try:
            if "".join(str(x.get("text") or "") for x in provided if isinstance(x, dict)) == text:
                segments = provided
        except (ValueError, TypeError):
            pass
    ts, iso = parse_time(m)
    media = media_from_message(m)
    forwarded = m.get("forwarded_from") or m.get("forward_from") or ""
    action = str(m.get("action") or "")
    service = str(m.get("type") or "message")
    if not text and action:
        text = action.replace("_", " ")
    if not text and isinstance(m.get("poll"), dict):
        question, _ = extract_text(m["poll"].get("question"))
        text = msg("import.poll", question=question or msg("import.poll_untitled"))
    if not text and m.get("sticker_emoji"):
        text = str(m["sticker_emoji"])
    if not text and m.get("location_information"):
        text = msg("import.location")
    # Only use media paths that actually exist; keep the previous export's media
    # and filename search tokens when a newer text-only export omits attachments.
    valid_media = []
    for item in media:
        full = (root / item["relpath"]).resolve()
        if full.is_relative_to(root) and full.is_file():
            valid_media.append(item)
    if audit is not None:
        audit["media_references"] += len(media)
        audit["media_present"] += len(valid_media)
        audit["media_missing"] += len(media) - len(valid_media)
    old_filenames = []
    if not valid_media:
        old_filenames = [row["filename"] for row in conn.execute(
            "SELECT md.filename FROM media md JOIN messages ms ON ms.id=md.message_id "
            "WHERE ms.chat_id=? AND ms.tg_id=?", (chat_id, str(tid)))]
    searchable = text + " " + " ".join(x["filename"] for x in valid_media) + " " + " ".join(old_filenames)
    reactions = m.get("reactions") if isinstance(m.get("reactions"), list) else []
    # All fields not shown in the UI remain accessible in 'extra_json'. Store entire
    # message to avoid silently throwing away unsupported/novel Telegram export fields.
    extras = json.dumps(m, ensure_ascii=False, default=str, separators=(",", ":"))
    try:
        conn.execute("""INSERT INTO messages(chat_id,tg_id,ts,date_iso,sender,sender_id,body,search_text,
            entities_json,type,action,reply_to,forwarded_from,edited,album_id,reactions_json,extra_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(chat_id,tg_id) DO UPDATE SET
            ts=excluded.ts,date_iso=excluded.date_iso,sender=excluded.sender,
            sender_id=excluded.sender_id,body=excluded.body,
            search_text=CASE WHEN excluded.search_text<>'' THEN excluded.search_text ELSE messages.search_text END,
            entities_json=excluded.entities_json,type=excluded.type,action=excluded.action,
            reply_to=excluded.reply_to,forwarded_from=excluded.forwarded_from,
            edited=excluded.edited,album_id=excluded.album_id,reactions_json=excluded.reactions_json,
            extra_json=excluded.extra_json""",
            (chat_id, str(tid), ts, iso, str(m.get("from") or m.get("actor") or ""),
             str(m.get("from_id") or m.get("actor_id") or ""), text, searchable.strip(),
             json.dumps(segments, ensure_ascii=False, default=str), service, action,
             str(m.get("reply_to_message_id")) if m.get("reply_to_message_id") is not None else None,
             str(forwarded), str(m.get("edited") or m.get("edited_unixtime") or "") or None,
             str(m.get("grouped_id")) if m.get("grouped_id") is not None else None,
             json.dumps(reactions, ensure_ascii=False, default=str), extras))
    except sqlite3.Error:
        raise
    msg_id = conn.execute("SELECT id FROM messages WHERE chat_id=? AND tg_id=?", (chat_id, str(tid))).fetchone()["id"]
    # Preserve previous valid media if a later export omitted media (text-only export).
    if valid_media:
        conn.execute("DELETE FROM media WHERE message_id=?", (msg_id,))
        conn.executemany("""INSERT INTO media(message_id,import_id,relpath,kind,filename,mime,width,height,file_size)
            VALUES(?,?,?,?,?,?,?,?,?)""", [
            (msg_id, import_id, x["relpath"], x["kind"], x["filename"], x["mime"], x["width"], x["height"], x["file_size"])
            for x in valid_media])
    return True


def import_export(path: str | Path, progress: bool = True) -> dict:
    source = Path(path).expanduser().resolve()
    if source.is_dir():
        source = source / "result.json"
    if not source.is_file():
        raise FileNotFoundError(f"result.json not found: {source}")
    root = source.parent.resolve()
    conn = connect()
    initialize(conn)
    started = time.time()
    cur = conn.execute("INSERT INTO imports(root,source_file,imported_at) VALUES(?,?,?)",
                       (str(root), str(source), int(started)))
    import_id = cur.lastrowid
    conn.commit()
    stats = {"chats": 0, "left_chats": 0, "messages": 0, "import_id": import_id,
             "media_references": 0, "media_present": 0, "media_missing": 0, "seconds": 0}
    current_chat: int | None = None
    touched: set[int] = set()
    try:
        for event, data in stream_events(source):
            if event == "profile":
                if data["key"] == "user_id":
                    set_config(conn, "me_id", str(data["value"]))
                elif data["key"] in ("first_name", "last_name"):
                    set_config(conn, "me_" + data["key"], str(data["value"]))
                    set_config(conn, "me_name", (get_config(conn, "me_first_name") + " " + get_config(conn, "me_last_name")).strip())
            elif event == "start":
                current_chat = ensure_chat(conn, data, import_id, root)
                touched.add(current_chat)
                stats["chats"] += 1
                if data.get("left_archive"):
                    stats["left_chats"] += 1
            elif event == "message" and current_chat is not None:
                if isinstance(data, dict) and process_message(conn, data, current_chat, import_id, root, stats):
                    stats["messages"] += 1
                    if stats["messages"] % 2000 == 0:
                        conn.commit()
                        if progress:
                            print(msg("import.progress", count=f"{stats['messages']:,}"), flush=True)
            elif event == "end":
                conn.commit()
                current_chat = None
        for cid in touched:
            row = conn.execute("""SELECT COUNT(*) n,COALESCE(MAX(ts),0) last_ts FROM messages WHERE chat_id=?""", (cid,)).fetchone()
            last = conn.execute("SELECT body FROM messages WHERE chat_id=? ORDER BY ts DESC,id DESC LIMIT 1", (cid,)).fetchone()
            conn.execute("UPDATE chats SET messages_count=?,last_ts=?,last_preview=? WHERE id=?",
                         (row["n"], row["last_ts"], (last["body"] or "")[:200] if last else "", cid))
        conn.execute("UPDATE imports SET messages_seen=? WHERE id=?", (stats["messages"], import_id))
        conn.commit()
    except Exception:
        conn.rollback()
        # Delete fully / partially imported import on error? Keep valid rows because
        # past commits might already have happened; mark incomplete for visibility.
        conn.execute("UPDATE imports SET messages_seen=-1 WHERE id=?", (import_id,))
        conn.commit()
        raise
    finally:
        conn.close()
    stats["seconds"] = round(time.time() - started, 1)
    return stats


def import_contacts_only(source_file: str | Path, *, conn: sqlite3.Connection | None = None) -> int:
    """Add the contacts section without re-indexing messages/media from a completed bundle.

    Never scans the other top-level sections into memory. Idempotent per import.
    It only saves contacts present at export time; absence is not proof of deletion.
    """
    source = Path(source_file).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    owned_conn = conn is None
    if owned_conn:
        conn = connect()
    try:
        initialize(conn)
        # Portable bundles store a relative root token, so lookup by result.json filename,
        # rather than assuming the original import root is an absolute Windows path.
        imports = conn.execute("SELECT id,root FROM imports ORDER BY id").fetchall()
        if not imports:
            raise ValueError(msg("import.contacts_first"))
        # Prefer the matching root so new exports do not replace earlier contacts.
        # Existing ready v0.2 bundles usually have only a single primary import.
        bundle_env = __import__('os').environ.get('TGARCHIVE_BUNDLE_ROOT')
        import_id = imports[0]['id']
        for row in reversed(imports):
            saved = row['root']
            if saved.startswith('@TGARCHIVE_BUNDLE@/') and bundle_env:
                saved = str(Path(bundle_env) / saved[len('@TGARCHIVE_BUNDLE@/'):])
            if Path(saved).resolve() == source.parent:
                import_id = row['id']
                break
        conn.execute("DELETE FROM contacts WHERE import_id=?", (import_id,))
        if ijson:
            with source.open('rb') as file:
                records = ijson.items(file, 'contacts.list.item')
                count = _write_contacts(conn, import_id, records)
        else:
            with source.open('r', encoding='utf-8') as file:
                root = json.load(file)
            records = (root.get('contacts') or {}).get('list') or []
            count = _write_contacts(conn, import_id, records)
        conn.commit()
        return count
    except Exception:
        conn.rollback()
        raise
    finally:
        if owned_conn:
            conn.close()


def _write_contacts(conn: sqlite3.Connection, import_id: int, records) -> int:
    total = 0
    for item in records:
        if not isinstance(item, dict):
            continue
        conn.execute("INSERT OR IGNORE INTO contacts "
            "(import_id, telegram_user_id, first_name, last_name, phone_number, exported_at) "
            "VALUES(?,?,?,?,?,?)",
            (import_id, str(item['user_id']) if item.get('user_id') is not None else None,
             str(item.get('first_name') or ''), str(item.get('last_name') or ''),
             str(item.get('phone_number') or ''), str(item.get('date') or '')))
        total += 1
    return total
