# copyright by berlonak
# telegram: @Kilax123
"""Private Telegram history API: cookie sessions, FTS search, authenticated media."""
from __future__ import annotations

import hashlib
import hmac
import json
import mimetypes
import os
import re
import secrets
import sqlite3
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__
from .db import connect, get_config, initialize

COOKIE_NAME = "tgarchive_session"
COOKIE_AGE = 60 * 60 * 24 * 7
PASS_HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
STATIC = Path(__file__).parent / "static"
FAILED: dict[str, deque] = defaultdict(deque)

@asynccontextmanager
async def lifespan(application: FastAPI):
    with connect() as conn:
        initialize(conn)
    yield


app = FastAPI(title="Telegram Archive", version=__version__, docs_url=None, redoc_url=None,
              openapi_url=None, lifespan=lifespan)
app.mount("/assets", StaticFiles(directory=str(STATIC)), name="assets")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    result = await call_next(request)
    result.headers["X-Content-Type-Options"] = "nosniff"
    result.headers["Referrer-Policy"] = "no-referrer"
    result.headers["X-Frame-Options"] = "DENY"
    result.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    result.headers["Cache-Control"] = "private, no-store"
    if not request.url.path.startswith("/api/media/"):
        result.headers["Content-Security-Policy"] = (
            "default-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'; "
            "connect-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; "
            "script-src 'self'; style-src 'self'; font-src 'self'"
        )
    if os.environ.get("TGARCHIVE_HTTPS", "0") == "1":
        result.headers["Strict-Transport-Security"] = "max-age=31536000"
    return result


@app.get("/", response_class=HTMLResponse)
def homepage():
    return FileResponse(STATIC / "index.html", media_type="text/html")


@app.get("/favicon.ico")
def favicon():
    return FileResponse(STATIC / "favicon.svg", media_type="image/svg+xml")


def get_database():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def require_login(request: Request, conn: sqlite3.Connection = Depends(get_database)) -> sqlite3.Connection:
    token = request.cookies.get(COOKIE_NAME, "")
    if len(token) != 64 or re.fullmatch(r"[0-9a-f]{64}", token) is None:
        raise HTTPException(status_code=401, detail="Требуется вход")
    digest = hashlib.sha256(token.encode()).hexdigest()
    record = conn.execute("SELECT expires_at FROM sessions WHERE token_hash=?", (digest,)).fetchone()
    if not record or record["expires_at"] < int(time.time()):
        raise HTTPException(status_code=401, detail="Сессия истекла")
    return conn


def check_origin(request: Request) -> None:
    """JSON endpoints + same-origin validation protect state-changing API routes."""
    site = request.headers.get("sec-fetch-site", "")
    if site == "cross-site":
        raise HTTPException(403, "Cross-origin request forbidden")
    origin = request.headers.get("origin")
    if origin:
        parsed = urlsplit(origin)
        if parsed.scheme not in ("http", "https") or parsed.netloc.lower() != request.headers.get("host", "").lower():
            raise HTTPException(403, "Origin mismatch")
        if os.environ.get("TGARCHIVE_HTTPS", "0") == "1" and parsed.scheme != "https":
            raise HTTPException(403, "HTTPS required")
    ctype = request.headers.get("content-type", "")
    if request.method == "POST" and not ctype.lower().startswith("application/json"):
        raise HTTPException(415, "application/json required")


def request_ip(request: Request) -> str:
    remote = request.client.host if request.client else "unknown"
    if os.environ.get("TGARCHIVE_TRUST_PROXY") != "1":
        return remote
    # ONLY trust explicitly listed local reverse-proxy addresses / CIDRs.
    # Docker bridge gateway must be added by the server administrator.
    try:
        import ipaddress
        addr = ipaddress.ip_address(remote)
        networks = os.environ.get("TGARCHIVE_TRUSTED_PROXY_CIDRS", "127.0.0.1/8,::1/128")
        permitted = any(addr in ipaddress.ip_network(item.strip(), strict=False)
                        for item in networks.split(",") if item.strip())
        if permitted:
            claimed = request.headers.get("x-real-ip", "")
            ipaddress.ip_address(claimed)
            return claimed
    except ValueError:
        pass
    return remote


class LoginBody(BaseModel):
    # Bounded so oversized bodies cannot make Argon2 hashing arbitrarily expensive.
    password: str = Field(max_length=1024)


@app.post("/api/auth/login")
def login(body: LoginBody, request: Request, response: Response, conn: sqlite3.Connection = Depends(get_database)):
    check_origin(request)
    ip = request_ip(request)
    now = time.time()
    failures = FAILED[ip]
    while failures and failures[0] < now - 900:
        failures.popleft()
    if len(failures) >= 6:
        raise HTTPException(status_code=429, detail="Слишком много попыток. Попробуйте через 15 минут.")
    saved = get_config(conn, "password_hash")
    if not saved:
        raise HTTPException(status_code=503, detail="Архив не настроен: запустите tgarchive init")
    valid = False
    try:
        valid = PASS_HASHER.verify(saved, body.password)
    except (VerifyMismatchError, InvalidHashError):
        pass
    if not valid:
        failures.append(now)
        raise HTTPException(status_code=401, detail="Неверный пароль")
    FAILED.pop(ip, None)
    token = secrets.token_hex(32)
    digest = hashlib.sha256(token.encode()).hexdigest()
    conn.execute("DELETE FROM sessions WHERE expires_at<?", (int(now),))
    conn.execute("INSERT INTO sessions(token_hash,expires_at,created_at) VALUES (?,?,?)",
                 (digest, int(now) + COOKIE_AGE, int(now)))
    conn.commit()
    response.set_cookie(COOKIE_NAME, token, max_age=COOKIE_AGE, path="/", httponly=True,
                        secure=os.environ.get("TGARCHIVE_HTTPS", "0") == "1", samesite="strict")
    return {"ok": True}


@app.get("/api/auth/me")
def me(conn: sqlite3.Connection = Depends(require_login)):
    return {"authenticated": True, "account": "Личный архив"}


@app.post("/api/auth/logout")
def logout(request: Request, response: Response, conn: sqlite3.Connection = Depends(require_login)):
    check_origin(request)
    token = request.cookies.get(COOKIE_NAME, "")
    conn.execute("DELETE FROM sessions WHERE token_hash=?", (hashlib.sha256(token.encode()).hexdigest(),))
    conn.commit()
    response.delete_cookie(COOKIE_NAME, path="/", samesite="strict",
                           secure=os.environ.get("TGARCHIVE_HTTPS", "0") == "1")
    return {"ok": True}


@app.get("/api/stats")
def stats(conn: sqlite3.Connection = Depends(require_login)):
    row = conn.execute("SELECT COUNT(*) chats,COALESCE(SUM(messages_count),0) messages FROM chats").fetchone()
    counts = {r["kind"]: r["count"] for r in conn.execute(
        "SELECT kind,COUNT(*) count FROM media WHERE kind != 'thumbnail' GROUP BY kind")}
    last = conn.execute("SELECT MAX(imported_at) imported_at FROM imports WHERE messages_seen>=0").fetchone()
    left = conn.execute("SELECT COUNT(*) n FROM chats WHERE left_archive=1").fetchone()["n"]
    return {"chats": row["chats"], "left_chats": left, "messages": row["messages"], "media": counts,
            "last_import": last["imported_at"], "me_id": get_config(conn, "me_id"),
            "me_name": get_config(conn, "me_name")}


@app.get("/api/chats")
def chats(q: str = Query("", max_length=150), category: str = "all", limit: int = Query(150, ge=1, le=1000), offset: int = Query(0, ge=0),
          conn: sqlite3.Connection = Depends(require_login)):
    params: list = []
    conditions = []
    if q.strip():
        conditions.append("title LIKE ? ESCAPE '\\'")
        params.append("%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%")
    if category == "left":
        conditions.append("left_archive=1")
    elif category in ("personal", "groups", "channels", "saved"):
        conditions.append("category=?")
        params.append(category)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    items = [dict(r) for r in conn.execute(
        f"SELECT id,title,kind,category,left_archive,messages_count,last_ts,last_preview,avatar_import_id,avatar_path FROM chats {where} "
        "ORDER BY (category='saved') DESC,last_ts DESC,title LIMIT ? OFFSET ?", (*params, limit + 1, offset))]
    return {"items": items[:limit], "has_more": len(items)>limit}


def message_rows(conn: sqlite3.Connection, clause: str, params: tuple, limit: int) -> list[dict]:
    # clause may only be assembled from constant SQL fragments in trusted endpoint code.
    rows = conn.execute(f"""SELECT m.id,m.chat_id,m.tg_id,m.ts,m.date_iso,m.sender,m.sender_id,
        m.body,m.entities_json,m.type,m.action,m.reply_to,m.forwarded_from,m.edited,m.album_id,
        m.reactions_json, r.body reply_body,r.sender reply_sender,
        (b.message_id IS NOT NULL) bookmarked
        FROM messages m LEFT JOIN messages r ON r.chat_id=m.chat_id AND r.tg_id=m.reply_to
        LEFT JOIN bookmarks b ON b.message_id=m.id
        WHERE {clause} LIMIT ?""", (*params, limit)).fetchall()
    result = [dict(r) for r in rows]
    ids = [r["id"] for r in result]
    if ids:
        placeholders = ",".join("?" for _ in ids)
        files: dict[int, list[dict]] = defaultdict(list)
        for media in conn.execute(f"SELECT id,message_id,kind,filename,mime,width,height,file_size FROM media "
                                  f"WHERE message_id IN ({placeholders}) ORDER BY (kind='thumbnail'),id", ids):
            m = dict(media)
            m["url"] = f"/api/media/{m['id']}"
            files[m["message_id"]].append(m)
        for m in result:
            m["media"] = files.get(m["id"], [])
            m["entities"] = json.loads(m.pop("entities_json") or "[]")
            m["reactions"] = json.loads(m.pop("reactions_json") or "[]")
            m["bookmarked"] = bool(m["bookmarked"])
    return result


@app.get("/api/chats/{chat_id}/messages")
def chat_messages(chat_id: int, before_ts: int | None = None, before_id: int | None = None,
                  after_ts: int | None = None, after_id: int | None = None,
                  around: int | None = None, limit: int = Query(50, ge=1, le=100),
                  conn: sqlite3.Connection = Depends(require_login)):
    if not conn.execute("SELECT 1 FROM chats WHERE id=?", (chat_id,)).fetchone():
        raise HTTPException(404, "Чат не найден")
    if around is not None:
        target = conn.execute("SELECT ts,id FROM messages WHERE id=? AND chat_id=?", (around, chat_id)).fetchone()
        if not target:
            raise HTTPException(404, "Сообщение не найдено")
        older_count = limit // 2
        newer_count = limit - older_count
        earlier = message_rows(conn, "m.chat_id=? AND (m.ts<? OR (m.ts=? AND m.id<?)) ORDER BY m.ts DESC,m.id DESC",
                               (chat_id, target["ts"], target["ts"], target["id"]), older_count + 1)
        centered = message_rows(conn, "m.chat_id=? AND (m.ts>? OR (m.ts=? AND m.id>=?)) ORDER BY m.ts ASC,m.id ASC",
                                (chat_id, target["ts"], target["ts"], target["id"]), newer_count + 1)
        items = list(reversed(earlier[:older_count])) + centered[:newer_count]
        return {"items": items, "has_more": len(earlier) > older_count,
                "has_newer": len(centered) > newer_count, "around": around}
    if (before_ts is None) != (before_id is None) or (after_ts is None) != (after_id is None):
        raise HTTPException(422, "Нужно указать время и ID сообщения")
    if before_ts is not None and after_ts is not None:
        raise HTTPException(422, "Нельзя одновременно загружать старые и новые сообщения")
    if after_ts is not None:
        clause = "m.chat_id=? AND (m.ts>? OR (m.ts=? AND m.id>?)) ORDER BY m.ts ASC,m.id ASC"
        params = (chat_id, after_ts, after_ts, after_id)
        items = message_rows(conn, clause, params, limit + 1)
        return {"items": items[:limit], "has_more": False, "has_newer": len(items) > limit}
    if before_ts is not None and before_id is not None:
        clause = "m.chat_id=? AND (m.ts<? OR (m.ts=? AND m.id<?)) ORDER BY m.ts DESC,m.id DESC"
        params = (chat_id, before_ts, before_ts, before_id)
    else:
        clause = "m.chat_id=? ORDER BY m.ts DESC,m.id DESC"
        params = (chat_id,)
    items = message_rows(conn, clause, params, limit + 1)
    more = len(items) > limit
    return {"items": list(reversed(items[:limit])), "has_more": more, "has_newer": False}


@app.get("/api/chats/{chat_id}/days")
def chat_days(chat_id: int, conn: sqlite3.Connection = Depends(require_login)):
    rows = conn.execute("SELECT substr(date_iso,1,10) day,COUNT(*) count FROM messages WHERE chat_id=? "
                        "GROUP BY day ORDER BY day DESC LIMIT 2000", (chat_id,)).fetchall()
    return {"days": [dict(row) for row in rows]}


def fts_expression(query: str) -> str:
    words = re.findall(r"[^\W_]+", query, flags=re.UNICODE)[:12]
    return " AND ".join('"' + w.replace('"', '""') + '"*' for w in words)


@app.get("/api/search")
def search(q: str = Query("", max_length=200), chat_id: int | None = None,
           sender: str = Query("", max_length=150), after: str = "", before: str = "", has: str = "",
           bookmarked: bool = False, offset: int = Query(0, ge=0, le=10000),
           limit: int = Query(40, ge=1, le=100), conn: sqlite3.Connection = Depends(require_login)):
    conditions: list[str] = []
    params: list = []
    joins = ""
    if q.strip():
        expression = fts_expression(q.strip())
        if not expression:
            return {"items": [], "has_more": False}
        joins += " JOIN messages_fts ON messages_fts.rowid=m.id"
        conditions.append("messages_fts MATCH ?")
        params.append(expression)
    if chat_id is not None:
        conditions.append("m.chat_id=?")
        params.append(chat_id)
    if sender.strip():
        conditions.append("m.sender LIKE ? ESCAPE '\\'")
        params.append("%" + sender.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%")
    for field, iso_date, op in (("after", after, ">="), ("before", before, "<=")):
        if iso_date:
            try:
                timestamp = int(datetime.strptime(iso_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
                if field == "before":
                    timestamp += 86400 - 1
            except ValueError:
                raise HTTPException(400, "Дата должна быть YYYY-MM-DD")
            conditions.append(f"m.ts {op} ?")
            params.append(timestamp)
    if has in ("photo", "video", "voice", "audio", "file", "link"):
        if has == "link":
            conditions.append("(m.search_text LIKE '%http://%' OR m.search_text LIKE '%https://%')")
        else:
            kinds = {"video": ("video", "video_message", "animation"),
                     "photo": ("photo",), "voice": ("voice",), "audio": ("audio",),
                     "file": ("file",)}[has]
            placeholders = ",".join("?" for _ in kinds)
            conditions.append(f"EXISTS(SELECT 1 FROM media md WHERE md.message_id=m.id AND md.kind IN ({placeholders}))")
            params.extend(kinds)
    if bookmarked:
        conditions.append("EXISTS(SELECT 1 FROM bookmarks bm WHERE bm.message_id=m.id)")
    if not conditions:
        return {"items": [], "has_more": False}
    where = " AND ".join(conditions)
    rows = conn.execute(f"""SELECT m.id,m.chat_id,m.ts,m.sender,m.body,m.type,c.title chat_title,c.category,
        EXISTS(SELECT 1 FROM media md WHERE md.message_id=m.id) has_media
        FROM messages m {joins} JOIN chats c ON c.id=m.chat_id
        WHERE {where} ORDER BY m.ts DESC,m.id DESC LIMIT ? OFFSET ?""", (*params, limit + 1, offset)).fetchall()
    return {"items": [dict(r) for r in rows[:limit]], "has_more": len(rows) > limit}


@app.get("/api/gallery")
def gallery(chat_id: int | None = None, kind: str = "all", offset: int = Query(0, ge=0, le=1000000),
            limit: int = Query(48, ge=1, le=100), conn: sqlite3.Connection = Depends(require_login)):
    conditions = ["md.kind != 'thumbnail'"]
    params: list = []
    if chat_id is not None:
        conditions.append("m.chat_id=?")
        params.append(chat_id)
    if kind == "all":
        conditions.append("md.kind IN ('photo','video','video_message','animation','sticker')")
    elif kind in ("photo", "video", "voice", "audio", "file", "sticker"):
        k = ("video", "video_message", "animation") if kind == "video" else (kind,)
        conditions.append("md.kind IN (" + ",".join("?" * len(k)) + ")")
        params.extend(k)
    else:
        raise HTTPException(400, "Неизвестный тип медиа")
    rows = conn.execute(f"""SELECT md.id,md.message_id,md.kind,md.filename,md.mime,md.width,md.height,
        m.chat_id,m.ts,m.sender,c.title chat_title
        FROM media md JOIN messages m ON m.id=md.message_id JOIN chats c ON c.id=m.chat_id
        WHERE {' AND '.join(conditions)} ORDER BY m.ts DESC,md.id DESC LIMIT ? OFFSET ?""",
        (*params, limit + 1, offset)).fetchall()
    return {"items": [{**dict(r), "url": f"/api/media/{r['id']}"} for r in rows[:limit]],
            "has_more": len(rows) > limit}


INLINE_MEDIA = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/avif",
                "video/mp4", "video/webm", "video/quicktime", "audio/ogg", "audio/mpeg", "audio/mp4", "audio/x-m4a", "audio/aac", "audio/wav", "audio/webm"}


def safe_file(conn: sqlite3.Connection, import_id: int, relpath: str) -> Path:
    row = conn.execute("SELECT root FROM imports WHERE id=?", (import_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Файл не найден")
    saved_root = row["root"]
    token = "@TGARCHIVE_BUNDLE@/"
    if saved_root.startswith(token):
        bundle_env = os.environ.get("TGARCHIVE_BUNDLE_ROOT")
        if not bundle_env:
            raise HTTPException(503, "Не указан TGARCHIVE_BUNDLE_ROOT")
        bundle = Path(bundle_env).resolve()
        relative = saved_root[len(token):].replace("\\", "/")
        if (not relative.startswith("exports/") or
                any(part in (".", "..") for part in relative.split("/"))):
            raise HTTPException(404, "Недопустимый путь к экспорту")
        root = (bundle / relative).resolve()
        exports_root = (bundle / "exports").resolve()
        if not exports_root.is_relative_to(bundle) or not root.is_relative_to(exports_root):
            raise HTTPException(404, "Путь вне архива")
    else:
        root = Path(saved_root).resolve()
    raw = relpath.replace("\\", "/")
    # Additional check at read time, including symlinks created after import.
    if (not raw or raw.startswith("/") or "\x00" in raw or re.match(r"^[A-Za-z]:", raw)
            or any(x in ("..", ".") for x in Path(raw).parts)):
        raise HTTPException(404, "Неверный путь")
    full = (root / raw).resolve()
    if not full.is_relative_to(root) or not full.is_file():
        raise HTTPException(404, "Исходный файл недоступен. Проверьте путь к экспорту.")
    return full


@app.get("/api/media/{media_id}")
def serve_media(media_id: int, download: bool = False, conn: sqlite3.Connection = Depends(require_login)):
    row = conn.execute("SELECT import_id,relpath,filename,mime FROM media WHERE id=?", (media_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Файл не найден")
    path = safe_file(conn, row["import_id"], row["relpath"])
    actual_mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    # Export metadata isn't trusted for active content / inline responses.
    inline = not download and actual_mime in INLINE_MEDIA
    return FileResponse(path, media_type=actual_mime if inline else "application/octet-stream",
                        filename=None if inline else Path(row["filename"]).name,
                        content_disposition_type="attachment" if not inline else "inline")


@app.get("/api/avatar/{chat_id}")
def avatar(chat_id: int, conn: sqlite3.Connection = Depends(require_login)):
    row = conn.execute("SELECT avatar_import_id,avatar_path FROM chats WHERE id=?", (chat_id,)).fetchone()
    if not row or not row["avatar_path"]:
        raise HTTPException(404, "Нет аватара")
    path = safe_file(conn, row["avatar_import_id"], row["avatar_path"])
    mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    if mime not in ("image/jpeg", "image/png", "image/webp", "image/gif", "image/avif"):
        raise HTTPException(404, "Неподдерживаемый аватар")
    return FileResponse(path, media_type=mime)


@app.get("/api/messages/{message_id}/raw")
def raw_message(message_id: int, conn: sqlite3.Connection = Depends(require_login)):
    row = conn.execute("SELECT extra_json FROM messages WHERE id=?", (message_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Сообщение не найдено")
    return JSONResponse(content=json.loads(row["extra_json"]))


@app.get("/api/bookmarks")
def bookmarks(limit: int = Query(100, ge=1, le=300), conn: sqlite3.Connection = Depends(require_login)):
    rows = conn.execute("""SELECT m.id,m.chat_id,m.ts,m.sender,m.body,c.title chat_title
        FROM bookmarks b JOIN messages m ON m.id=b.message_id JOIN chats c ON c.id=m.chat_id
        ORDER BY b.created_at DESC LIMIT ?""", (limit,)).fetchall()
    return {"items": [dict(r) for r in rows]}


@app.post("/api/bookmarks/{message_id}")
def add_bookmark(message_id: int, request: Request, conn: sqlite3.Connection = Depends(require_login)):
    check_origin(request)
    if not conn.execute("SELECT 1 FROM messages WHERE id=?", (message_id,)).fetchone():
        raise HTTPException(404, "Сообщение не найдено")
    conn.execute("INSERT OR IGNORE INTO bookmarks(message_id,created_at) VALUES(?,?)", (message_id, int(time.time())))
    conn.commit()
    return {"bookmarked": True}


@app.delete("/api/bookmarks/{message_id}")
def delete_bookmark(message_id: int, request: Request, conn: sqlite3.Connection = Depends(require_login)):
    check_origin(request)
    conn.execute("DELETE FROM bookmarks WHERE message_id=?", (message_id,))
    conn.commit()
    return {"bookmarked": False}

@app.get("/api/chats/{chat_id}/resolve")
def resolve_reply(chat_id: int, tg_id: str = Query(..., max_length=40),
                  conn: sqlite3.Connection = Depends(require_login)):
    row = conn.execute("SELECT id FROM messages WHERE chat_id=? AND tg_id=?", (chat_id, tg_id)).fetchone()
    if not row:
        raise HTTPException(404, "Сообщение отсутствует в экспорте")
    return {"id": row["id"]}


@app.get("/api/contacts")
def contacts(q: str = Query("", max_length=120), offset: int = Query(0, ge=0, le=100000),
             limit: int = Query(60, ge=1, le=100), conn: sqlite3.Connection = Depends(require_login)):
    """Only exports' saved contacts, not a claim about historic/deleted contacts."""
    parameters: list = []
    where = ""
    if q.strip():
        escaped = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        where = "WHERE first_name LIKE ? ESCAPE '\\' OR last_name LIKE ? ESCAPE '\\' OR phone_number LIKE ? ESCAPE '\\'"
        parameters.extend([f"%{escaped}%"] * 3)
    results = conn.execute(f"""SELECT id,telegram_user_id,first_name,last_name,phone_number,exported_at
        FROM contacts {where} ORDER BY first_name COLLATE NOCASE,last_name COLLATE NOCASE
        LIMIT ? OFFSET ?""", (*parameters, limit + 1, offset)).fetchall()
    return {"items": [dict(x) for x in results[:limit]], "has_more": len(results) > limit}
