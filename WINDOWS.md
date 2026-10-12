# Building from scratch on Windows (one folder)

**You need:** Windows 10/11, **Python 3.10+** installed with the `py -3` launcher, internet access for the first dependency install, and one Telegram Desktop export folder that contains **`result.json`, the HTML files and all media side by side**. You do not need to point to two folders.

**Message language.** The scripts and dialogs use Russian when Windows is in Russian (or Ukrainian, Belarusian, Kazakh) and English otherwise. To choose explicitly, run `set TGARCHIVE_LANG=en` (or `ru`) in CMD and start the `.bat` file from that same window. Русская версия: [WINDOWS-RU.md](WINDOWS-RU.md).

1. Download the source (`git clone`, or *Code → Download ZIP* on GitHub) and unpack it into its own folder, for example `D:\tgarchive-builder`. Make sure it contains `START-HERE.bat` and `bundletool.py`.
2. Make a **separate backup** of the original export. By default the script *moves* the source folder on the **same drive** into a new `TelegramArchive-ready/exports/first-export` to save disk space. This is not a copy and not a backup. File bytes are not changed, but **the source folder changes its path**.
3. Double-click `START-HERE.bat`. Enter **one path**, for example `D:\TelegramExport` (it must contain `result.json`). By default the bundle is built next to it in `TelegramArchive-ready`. If a **finished** build is already there, do not run the import again; use it or choose another `BundlePath`. If a folder from an unfinished run is left over, see the recovery section below.
4. Once you have a backup, confirm the move by typing `MOVE` (with Russian messages: `ПЕРЕМЕСТИТЬ`; in copy mode: `COPY` / `КОПИРОВАТЬ`). **Before the move** two password dialogs open (at least 12 characters): paste with **Ctrl+V**, not Shift+Insert in CMD. After confirmation the script moves the export, builds SQLite/FTS and verifies the JSON, the database and the media links. For a large export wait for `DONE`. The password is passed to the app locally and is never written in plain text to a command line or file.
5. You should get `TelegramArchive-ready` with `bundle-manifest.json`, `app/`, `data/archive.sqlite3`, `exports/first-export/`, `deploy/` **and** `START-LOCAL.bat`. What matters is the `DONE` message, not just a new folder: after an error an **incomplete folder** may remain.
6. Double-click **`TelegramArchive-ready/START-LOCAL.bat`** (it is already there). Open **`http://127.0.0.1:8000`** and enter the password. Stop it with `Ctrl+C` in the console. On Windows this is **local access from your own computer only**, not for other devices.

### If the ready folder already exists / you do not want to move the original

Open PowerShell in the **builder** folder and run the *copy variant* if you have **free space equal to the export size**:

```powershell
.\build-one-folder-windows.ps1 -ExportPath "D:\TelegramExport" -BundlePath "D:\TelegramArchive-ready-NEW" -CopyExport
```

To move into a differently named destination folder (the second path must be on the same drive):

```powershell
.\build-one-folder-windows.ps1 -ExportPath "D:\TelegramExport" -BundlePath "D:\TelegramArchive-ready-NEW"
```

**If your export currently lives inside an old `TelegramArchive-ready`:** moving it out leaves the old reader without media. Copy the export to a separate safe place first, or keep using the old ready folder if you do not need to rebuild the index.

### Verification and a single file for transfer

To repeat the verification before a transfer (stop the local reader first):

```powershell
.\.venv\Scripts\python.exe .\bundletool.py verify --bundle "D:\TelegramArchive-ready" --full
```

**Recommended:** transfer the whole ready folder over **SFTP with resume**. If you really need one file, create an **uncompressed** `tgarchive.tar`:

```powershell
.\.venv\Scripts\python.exe .\bundletool.py pack --bundle "D:\TelegramArchive-ready" --output "D:\tgarchive.tar"
```

The TAR is about the size of the folder plus the index. You need that much extra space on Windows, plus space for unpacking on the server. **The TAR is a portable archive, not a Docker container.**

### Notes

- The ready folder automatically includes all fixes; no separate patches are needed.
- If the console shows an error, **do not delete `result.json` or the ready folder before you understand it**. Never upload an incomplete bundle to a server.
- If you built `TelegramArchive-ready` with an older builder and everything works, a rebuild is **not required**.

### Recovering from "file is used by another process" or mismatched passwords

**Never delete the original export or an incomplete `ready` folder until you have checked both folders.**

1. Close `START-LOCAL.bat`, Python processes, export files open in VS Code and extra Explorer windows. Check **where `result.json` actually is**:
   - If it is in the original `D:\TelegramExport\result.json` and `ready/exports/` has **no files**, run `START-HERE.bat` again. The script safely reuses the empty staging folder and asks for the password again before the move.
   - If the original `result.json` has **already been moved** to `D:\TelegramArchive-ready\exports\first-export\result.json` and there is no `bundle-manifest.json` yet: run `RESUME-READY.bat` from the builder folder and point it to the existing `TelegramArchive-ready`. It works **without moving the export again**, but refuses to continue if the database is already partly imported.
   - If data is **in both folders**, first find out whether each copy is complete. Do not delete anything and do not start another move on top of incomplete data.
2. If `bundle-manifest.json` **exists** and the local app already works, **do not rebuild the archive because of the password**: stop `START-LOCAL.bat` and run `RESET-PASSWORD.bat` in the ready folder. Messages and media stay unchanged.
3. If the move keeps failing with "used by another process", run **`CHECK-LOCK.bat`** (or wait for it to start automatically after the error). Enter the export folder, allow the UAC prompt and, if you agree, confirm the download of the **official** Microsoft Sysinternals Handle. Process names, PIDs and open paths, **if any are found**, are shown on screen and saved to `%TEMP%/tgarchive-lock-*.txt`. An open handle does not prove that it blocks the move; if none are found, the cause may be something else. The builder still uses a plain `Move-Item`; **no hardlinks are used**.

**Limitation:** this version is tested by automated tests on a small synthetic export. Keep an independent backup before processing your personal archive.
