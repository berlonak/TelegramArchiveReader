# Telegram Archive Reader

[![Tests](https://github.com/berlonak/TelegramArchiveReader/actions/workflows/tests.yml/badge.svg)](https://github.com/berlonak/TelegramArchiveReader/actions/workflows/tests.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)

**A private, read-only web viewer with full-text search for Telegram Desktop JSON exports.**
Point it at the folder Telegram Desktop exported and browse every chat, group and channel,
search across the whole history, and open photos and videos. Everything happens on your own
machine or server. It does not connect to Telegram, use the API or ask for your Telegram login.

[Русская версия](README.ru.md)

![Chat view](docs/screenshots/chat.png)

## Why

Telegram Desktop can export your whole account, but its HTML export is split into many
separate pages and has no search across chats. The machine-readable JSON export has all the
data, but it can't be browsed. This project indexes that JSON into SQLite with full-text
search and puts a fast, Telegram-like web interface on top. Large exports work too, because
the importer streams the JSON one message at a time and media files are never copied.

## Features

- **Imports Telegram Desktop "Machine-readable JSON" exports**: full-account exports (chats,
  left chats, contacts, account name) and single-chat exports.
- **Streaming import** with `ijson`: only one message is held in memory, so exports of tens of
  gigabytes are fine. Original export files are never modified.
- **Incremental re-import**: importing a newer export updates existing messages without
  duplicates. If the newer export is text-only, media found by the earlier import are kept.
- **Full-text search** (SQLite FTS5, prefix matching) across all chats, including attachment
  file names. Filters: chat, sender, date range, and "contains photo / video / voice / audio /
  file / link".
- **Chat view**: infinite scrolling in both directions, jump to a date, jump from a search
  hit into the conversation, reply previews with a jump to the original message.
- **Chat categories**: personal, groups, channels, Saved Messages and chats you have left.
- **Media library**: photos, videos, voice messages, audio, files and stickers, with an
  in-browser viewer and downloads.
- **Bookmarks**, **contacts from the export**, and the **raw JSON** of any message (every
  export field is preserved, including ones the UI does not show).
- **English and Russian interface** with a one-click switch (menu or sign-in page). The
  language follows the browser by default and the choice is remembered.
- Dark and light themes, mobile layout, `Ctrl/⌘ + K` for search.
- **Portable bundle**: index once on Windows, then copy the ready folder to a Linux VPS
  without re-indexing. Includes integrity checks (SHA-256 of `result.json`, file count and
  total size) and a one-command Ubuntu/Debian installer.

| Overview | Search | Mobile |
|---|---|---|
| ![Overview](docs/screenshots/home.png) | ![Search](docs/screenshots/search.png) | ![Mobile](docs/screenshots/mobile.png) |

> More languages are welcome: a translation is a single dictionary in
> [`tgarchive/static/i18n.js`](tgarchive/static/i18n.js), see [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

The archive contains your private correspondence, so the web app is locked down by default:

- One archive password, stored as an **Argon2id** hash (minimum 12 characters).
- Session cookies are `HttpOnly`, `SameSite=Strict` and `Secure` behind HTTPS; only a SHA-256
  hash of each session token is stored.
- Login rate limiting: 6 failed attempts per IP lock logins from it for 15 minutes.
- Strict Content-Security-Policy, `X-Frame-Options: DENY`, `nosniff`, `no-referrer`,
  `Cache-Control: no-store`, and Origin checks on state-changing requests.
- Media paths are checked against path traversal and symlinks at import time **and** on every
  request. Only safe media types are served inline; everything else is a download.
- The app binds to `127.0.0.1` only. Internet access goes through nginx with HTTPS.

The password and HTTPS protect web access. They do **not** encrypt the files on disk, so keep
encrypted backups and never publish your export or the ready bundle.

## Quick start

Requirements: Python 3.10+ (Linux, macOS or Windows).

```bash
git clone https://github.com/berlonak/TelegramArchiveReader.git
cd TelegramArchiveReader
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .

tgarchive init                     # set the archive password
tgarchive import examples/demo-export-en   # synthetic demo data; or the path to your export
tgarchive serve                    # http://127.0.0.1:8000
```

Media are served from the original export folder, so keep it at the same path after import.
The index is stored in `./archive-data/` unless `TGARCHIVE_DATA_DIR` is set.

### Exporting from Telegram Desktop

*Settings → Advanced → Export Telegram data*. Choose the format **Machine-readable JSON** and
tick the media types you want. To export a single chat, open the chat menu and pick
*Export chat history* → JSON. Pass the folder that contains `result.json` to
`tgarchive import`.

### CLI

| Command | Purpose |
|---|---|
| `tgarchive init` | Show the data directory and set the password |
| `tgarchive import PATH` | Import a folder with `result.json` (or the file itself) |
| `tgarchive serve [--port 8000]` | Start the web app on `127.0.0.1` |
| `tgarchive change-password` | Change the password and end all sessions |
| `tgarchive stats` | Number of chats, messages and media |
| `tgarchive reindex` | Rebuild the FTS5 search index |

## Windows: build a portable archive

For a large export the recommended flow is the Windows builder. Double-click
`START-HERE.bat`, enter the export folder, and confirm. It asks for the password **before**
touching the export, moves the export (same drive, no copy) into `TelegramArchive-ready`,
builds the index and verifies it. Then run `TelegramArchive-ready\START-LOCAL.bat` and open
<http://127.0.0.1:8000>.

`RESUME-READY.bat` recovers an interrupted build. `RESET-PASSWORD.bat` changes the password
without re-importing. `CHECK-LOCK.bat` shows which processes hold files open when Windows
refuses to move the folder (it uses Microsoft Sysinternals Handle, downloaded only with your
consent and checked for Microsoft's signature).

Detailed guide (Russian): [WINDOWS-RU.md](WINDOWS-RU.md).

## Server deployment (Ubuntu/Debian, no Docker)

Upload the ready folder via SFTP, verify it, then install:

```bash
sudo mv ~/tgarchive-upload /srv/tgarchive
sudo python3 /srv/tgarchive/bundletool.py verify --bundle /srv/tgarchive --full
sudo bash /srv/tgarchive/deploy/install-bundle.sh PUBLIC_IP EMAIL
```

The installer sets up a hardened systemd service (`tgarchive`, localhost only), nginx and a
Let's Encrypt **IP-address certificate** (Certbot 5.4+, short-lived profile, renewal timer).
No domain name is required. The script is designed for a clean server; review it first if
nginx already serves other sites.

Detailed guide (Russian): [SERVER-RU.md](SERVER-RU.md). An optional Docker Compose template
lives in [`deploy/docker/compose.yaml`](deploy/docker/compose.yaml); it keeps your data
outside the image.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `TGARCHIVE_DATA_DIR` | `./archive-data` | Directory with `archive.sqlite3` |
| `TGARCHIVE_HTTPS` | `0` | `1` behind HTTPS: secure cookies, HSTS, HTTPS-only Origin |
| `TGARCHIVE_TRUST_PROXY` | unset | `1` to take the client IP from `X-Real-IP` sent by a trusted proxy |
| `TGARCHIVE_TRUSTED_PROXY_CIDRS` | `127.0.0.1/8,::1/128` | Proxy addresses whose `X-Real-IP` is trusted |
| `TGARCHIVE_BUNDLE_ROOT` | unset | Root of a portable bundle; set automatically by `start-local.py` |

## Limitations

- Read-only. It shows exactly what Telegram Desktop put in the JSON. Messages deleted before
  the export cannot be recovered.
- Messages are indexed from the JSON only. An HTML export in the same folder is kept but not
  parsed.
- Contacts are the list at export time. A missing contact does not mean it was deleted.
- Automated tests use small synthetic exports. Keep an independent backup before processing
  your real archive.

## Project structure

```
tgarchive/          FastAPI app, importer, SQLite schema, CLI, static web UI
bundletool.py       prepare / verify / pack / activate portable bundles
start-local.py      local launcher copied into the ready bundle
*.bat, *.ps1        Windows builder, recovery and diagnostics
deploy/             systemd units, nginx + Let's Encrypt setup, Docker Compose
examples/           synthetic demo exports in English and Russian (no real data)
tests/              pytest suite
```

## Development

```bash
pip install -e ".[test]"
python -m pytest -q tests
```

See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).
Changes are listed in [CHANGELOG.md](CHANGELOG.md).

## License

[Apache License 2.0](LICENSE). See also [NOTICE](NOTICE).

This is an independent project. It is not affiliated with, endorsed by, or sponsored by Telegram.
