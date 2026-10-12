# Changelog

Versions before 0.3.4 were not published. Their entries are reconstructed from code comments,
documentation and regression tests.

## [0.4.0] - 2026-10-12

### Added
- English web interface alongside Russian. Switch it in the menu or on the sign-in page; the
  default follows the browser language and the choice is stored locally. Dates and numbers
  are formatted for the selected language, message counts use proper plural forms, and known
  server error messages are translated.
- `examples/demo-export-en`: the synthetic demo export with English texts.
- A test that every UI string key exists in both dictionaries.

### Fixed
- A wrong password on the sign-in page was reported as "session ended" instead of
  "wrong password".
- Chat headers said "1 сообщений": message counts now use correct plural forms.

## [0.3.4] - 2026-10-12

First public release.

### Fixed
- `deploy/configure-https-ip.sh` was empty, so `install-bundle.sh` reported success without
  configuring nginx or HTTPS. It now sets up nginx, tests issuance on the Let's Encrypt
  staging environment, requests a short-lived IP-address certificate (Certbot 5.4+, webroot)
  with an nginx reload hook, and enables the HTTPS reverse proxy.
- The standalone `deploy/tgarchive.service` did not trust `X-Real-IP` from nginx, so login
  rate limiting counted every client as `127.0.0.1`.
- The search filter by sender treated `%` and `_` as SQL wildcards.
- The login password length is now bounded (1024 characters) before Argon2 hashing.
- `RESET-PASSWORD.bat` and `RESUME-READY.bat` used LF line endings, which can break `goto`
  labels in `cmd.exe`. All batch files now use CRLF (enforced by `.gitattributes`).
- Version numbers in the package, the web app and the builder are now consistent.
- `build-one-folder-windows.ps1 -StrictSnapshot` takes the expected counts as
  `-ExpectChatRecords` / `-ExpectMessageRecords` instead of hard-coded values.

### Added
- Lock diagnostics for a failed Windows move (`CHECK-LOCK.bat`) using Microsoft Sysinternals
  Handle, downloaded only with consent and verified by its Microsoft signature.
- English README, screenshots, CI, Apache-2.0 license.

### Changed
- The Windows builder uses a plain `Move-Item` again; the intermediate staging / hardlink
  approach was dropped.

## [0.3.2]

### Fixed
- The password was entered in a CMD console where pasting (Shift+Insert) was unreliable,
  which produced mismatched passwords. It is now entered in Tk dialogs with Ctrl+V and
  confirmed **before** the export is moved.
- After an early failed move (v0.3.1) an empty `ready/exports` folder blocked a rebuild. The
  builder now reuses an empty staging folder. `RESUME-READY` continues a build whose export
  was already moved and detects a split move (files left in both folders).

### Added
- `RESET-PASSWORD.bat`: change the password of a finished bundle without re-importing.

## [0.3]

### Fixed
- After jumping to a search hit you could not scroll to newer messages. Paging now works in
  both directions (`around`, `before_*`, `after_*`) with a stable `(timestamp, id)` order, so
  messages with identical timestamps are neither duplicated nor skipped.
- The chat jumped while loading older pages, because every page re-rendered the whole list and
  reset image sizes. Existing DOM nodes are kept, the position is anchored to a visible
  message, and a duplicate day separator is removed.
- Running a bundle locally required `bundletool activate`, which wrote absolute Windows paths
  into SQLite and broke the later move to Linux. Paths are now stored relative to the bundle
  and resolved through `TGARCHIVE_BUNDLE_ROOT`.
- Hotfixes no longer have to be downloaded separately; the ready bundle contains the local
  launcher and all fixes.

### Removed
- The informational block on the overview page.

### Added
- Contacts can be indexed into existing v0.2 bundles without re-importing messages.
- A text-only re-export no longer drops media found by an earlier import.

## [0.1]

- Initial version. Databases from 0.1 are upgraded automatically (the `left_archive` column
  for left chats is added on open).
