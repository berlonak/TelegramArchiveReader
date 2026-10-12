# copyright by berlonak
# telegram: @Kilax123
"""Bilingual (Russian / English) console messages for the CLI, bundletool and launchers.

Standard library only: bundletool.py imports this on servers before dependencies exist.
Language: TGARCHIVE_LANG=ru|en, otherwise the OS language, otherwise English.
"""
from __future__ import annotations

import os
import sys

LANGUAGES = ("ru", "en")
# Windows primary language IDs and POSIX prefixes that get the Russian interface.
_RU_LANGIDS = {0x19, 0x22, 0x23, 0x3F}  # Russian, Ukrainian, Belarusian, Kazakh
_RU_PREFIXES = ("ru", "uk", "be", "kk")


def language() -> str:
    forced = os.environ.get("TGARCHIVE_LANG", "").strip().lower()
    if forced in LANGUAGES:
        return forced
    if sys.platform == "win32":
        try:
            import ctypes
            langid = ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF
            return "ru" if langid in _RU_LANGIDS else "en"
        except (AttributeError, OSError):
            pass
    for name in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(name, "")
        if value:
            return "ru" if value.lower().startswith(_RU_PREFIXES) else "en"
    return "en"


def msg(key: str, **values) -> str:
    text = MESSAGES[key][0 if language() == "ru" else 1]
    return text.format(**values) if values else text


MESSAGES: dict[str, tuple[str, str]] = {
    # Shared
    "error": ("Ошибка: {message}", "Error: {message}"),
    "password_prompt": ("Пароль (не менее 12 символов): ", "Password (at least 12 characters): "),
    "password_repeat": ("Повтори пароль: ", "Repeat the password: "),
    "password_new": ("Новый пароль (не менее 12 символов): ", "New password (at least 12 characters): "),
    # tgarchive CLI
    "cli.too_short": ("пароль должен содержать минимум 12 символов.", "the password must be at least 12 characters long."),
    "cli.mismatch": ("пароли не совпали.", "the passwords do not match."),
    "cli.saved": ("Пароль сохранён (Argon2id), старые сессии сброшены.",
                  "Password saved (Argon2id); existing sessions were ended."),
    "cli.description": ("Telegram Archive — личный архив Telegram Desktop JSON",
                        "Telegram Archive — private viewer for Telegram Desktop JSON exports"),
    "cli.init": ("Первичная настройка и пароль", "Initial setup and password"),
    "cli.change_password": ("Сменить пароль и завершить все сессии", "Change the password and end all sessions"),
    "cli.import": ("Импортировать полный экспорт или отдельный чат", "Import a full export or a single chat"),
    "cli.import_path": ("Путь к каталогу с result.json или к самому файлу",
                        "Path to the folder with result.json, or to the file itself"),
    "cli.serve": ("Запустить веб-сервер (только localhost)", "Start the web server (localhost only)"),
    "cli.port": ("Порт (по умолчанию 8000)", "Port (default 8000)"),
    "cli.stats": ("Статистика базы данных", "Database statistics"),
    "cli.reindex": ("Восстановить поисковый индекс FTS5", "Rebuild the FTS5 search index"),
    "cli.data_dir": ("Каталог данных: {path}", "Data directory: {path}"),
    "cli.reading": ("Читаю JSON без изменения оригинальных файлов...", "Reading JSON; original files are not modified..."),
    "cli.keep_export": ("Важно: сохраняйте оригинальный каталог экспорта по этому пути: медиа берутся из него.",
                        "Important: keep the original export folder at this path; media are served from it."),
    "cli.need_password": ("Сначала задайте пароль: tgarchive init", "Set a password first: tgarchive init"),
    "cli.stats_line": ("Чатов: {chats}; сообщений: {messages}; медиа: {media}",
                       "Chats: {chats}; messages: {messages}; media: {media}"),
    "cli.reindexed": ("Поисковый индекс восстановлен.", "Search index rebuilt."),
    # Importer (placeholders are stored in the index in the language of the import)
    "import.progress": ("  Прочитано сообщений: {count}", "  Messages read: {count}"),
    "import.saved_title": ("Избранное", "Saved Messages"),
    "import.untitled": ("Без названия", "Untitled"),
    "import.poll": ("Опрос: {question}", "Poll: {question}"),
    "import.poll_untitled": ("без названия", "untitled"),
    "import.location": ("Геопозиция", "Location"),
    "import.contacts_first": ("Сначала импортируйте архив сообщений", "Import the message archive first"),
    # Local launcher (start-local.py)
    "local.incomplete": ("Неполный готовый архив. Отсутствует:\n{missing}",
                         "The ready archive is incomplete. Missing:\n{missing}"),
    "local.not_bundle": ("Это не переносимый архив Telegram Archive.", "This is not a portable Telegram Archive bundle."),
    "local.no_json": ("Исходный result.json не найден в готовой папке.", "The original result.json is missing from the ready folder."),
    "local.no_password": ("В базе нет пароля. Проверь полноту готового пакета.",
                          "The database has no password. Check that the ready bundle is complete."),
    "local.summary": ("Telegram Archive: {chats} чатов; {messages} сообщений.",
                      "Telegram Archive: {chats} chats; {messages} messages."),
    "local.open": ("ОТКРОЙ: http://127.0.0.1:8000", "OPEN: http://127.0.0.1:8000"),
    "local.password_hint": ("Вводи пароль, который задавал при подготовке архива.",
                            "Use the password you set while preparing the archive."),
    "local.stop_hint": ("Для остановки нажми Ctrl+C в этом окне. Не открывай порт 8000 наружу.",
                        "Press Ctrl+C in this window to stop. Do not expose port 8000 to the network."),
    "local.stopped": ("Остановлено.", "Stopped."),
    # bundletool: export inventory
    "bt.symlink_dir": ("В экспорте символическая ссылка на папку: {path}", "The export contains a folder symlink: {path}"),
    "bt.special_file": ("В экспорте ссылка или нестандартный файл: {path}", "The export contains a link or special file: {path}"),
    # bundletool: password dialogs
    "bt.no_tk": ("Python установлен без Tkinter. Установи Python с компонентом Tcl/Tk "
                 "либо запусти команду без --gui (ввод в консоли, не через Shift+Insert).",
                 "Python was installed without Tkinter. Install Python with the Tcl/Tk component "
                 "or run the command without --gui (console input; do not paste with Shift+Insert)."),
    "bt.dlg_title": ("Telegram Archive — пароль", "Telegram Archive — password"),
    "bt.dlg_prompt": ("Вставь пароль через Ctrl+V (не менее 12 символов):", "Paste the password with Ctrl+V (at least 12 characters):"),
    "bt.dlg_confirm_title": ("Telegram Archive — подтверждение", "Telegram Archive — confirmation"),
    "bt.dlg_confirm": ("Вставь ТОТ ЖЕ пароль ещё раз через Ctrl+V:", "Paste the SAME password again with Ctrl+V:"),
    "bt.dlg_error_title": ("Пароль", "Password"),
    "bt.dlg_too_short": ("Пароль должен содержать минимум 12 символов.", "The password must be at least 12 characters long."),
    "bt.dlg_mismatch": ("Пароли не совпали. Повтори ввод. Проверь, не добавлены ли пробелы при копировании.",
                        "The passwords do not match. Try again and check for extra spaces from copying."),
    "bt.dlg_cancelled": ("Ввод пароля отменён. Экспорт не будет перемещён.", "Password entry cancelled. The export will not be moved."),
    "bt.dlg_three_tries": ("Пароль не подтверждён за три попытки. Экспорт не перемещён.",
                           "The password was not confirmed in three attempts. The export was not moved."),
    # bundletool: preflight / reset / ask password
    "bt.partial_db_ready": ("В папке уже есть незавершённая база с данными. "
                            "Не перезаписывай её; остановись и проверь содержимое папки ready.",
                            "The folder already has an unfinished database with data. "
                            "Do not overwrite it; stop and inspect the ready folder."),
    "bt.preflight_bad": ("Пароли не совпали или короче 12 символов. Экспорт НЕ перемещён.",
                         "The passwords do not match or are shorter than 12 characters. The export was NOT moved."),
    "bt.preflight_ok": ("Пароль подтверждён и сохранён в виде хеша Argon2id. Экспорт пока не перемещён.",
                        "Password confirmed and stored as an Argon2id hash. The export has not been moved yet."),
    "bt.reset_stop_first": ("Останови START-LOCAL.bat перед сменой пароля.", "Stop START-LOCAL.bat before changing the password."),
    "bt.reset_no_db": ("База не найдена. Укажи папку готового архива.", "Database not found. Point to a ready archive folder."),
    "bt.reset_bad": ("Пароли не совпали или короче 12 символов. Ничего не изменено.",
                     "The passwords do not match or are shorter than 12 characters. Nothing was changed."),
    "bt.reset_no_password": ("Нет установленного пароля; проверь, что это готовая база.",
                             "No password is set; check that this is a finished database."),
    "bt.reset_ok": ("Пароль обновлён; все прежние сессии сброшены. Сообщения и медиа не затронуты.",
                    "Password updated; all previous sessions were ended. Messages and media were not touched."),
    "bt.password_exists": ("Пароль уже существует; сохраняю его без изменений.", "A password already exists; keeping it unchanged."),
    "bt.archive_password": ("Пароль архива (минимум 12 символов): ", "Archive password (at least 12 characters): "),
    "bt.password_bad": ("Пароли не совпали или короче 12 символов.", "The passwords do not match or are shorter than 12 characters."),
    # bundletool: prepare
    "bt.import_outside": ("Импорт {id} ссылается на файлы ВНЕ набора: {root}. "
                          "Пересобери набор или перемести каждый экспорт в bundle/exports/.",
                          "Import {id} refers to files OUTSIDE the bundle: {root}. "
                          "Rebuild the bundle or move every export into bundle/exports/."),
    "bt.no_result_json": ("Не найден result.json в {root}", "result.json not found in {root}"),
    "bt.install_deps": ("Сначала установи зависимости: python -m pip install -e .  "
                        "(Для больших экспортов обязателен потоковый парсер ijson.)",
                        "Install the dependencies first: python -m pip install -e .  "
                        "(The ijson streaming parser is required for large exports.)"),
    "bt.no_export_dir": ("Нет каталога экспорта: {path}", "Export folder not found: {path}"),
    "bt.bundle_inside_export": ("Каталог набора нельзя размещать ВНУТРИ исходного экспорта.",
                                "The bundle folder cannot be INSIDE the source export."),
    "bt.export_outside": ("Экспорт находится вне bundle/exports. Для большого экспорта перемести папку "
                          "в <bundle>/exports/first-export БЕЗ копирования; или передай --copy-export "
                          "(потребуется дополнительно столько же места, сколько занимает экспорт).",
                          "The export is outside bundle/exports. For a large export, move the folder "
                          "to <bundle>/exports/first-export WITHOUT copying, or pass --copy-export "
                          "(this needs as much free space again as the export takes)."),
    "bt.dest_exists": ("Папка назначения уже есть: {path}", "The destination folder already exists: {path}"),
    "bt.copy_into_self": ("Нельзя копировать экспорт в самого себя.", "Cannot copy the export into itself."),
    "bt.copying": ("Копирую экспорт без загрузки файлов в память; нужно свободное место не меньше объёма экспорта...",
                   "Copying the export without loading files into memory; free space of at least the export size is needed..."),
    "bt.export_not_direct": ("Экспорт должен лежать непосредственно внутри bundle/exports/<название>.",
                             "The export must be directly inside bundle/exports/<name>."),
    "bt.source": ("Исходный Telegram-экспорт: {path}", "Source Telegram export: {path}"),
    "bt.structure": ("Структура: {kind}", "Structure: {kind}"),
    "bt.structure_combined": ("JSON + HTML в одной папке", "JSON + HTML in one folder"),
    "bt.inventory": ("Проверяю число и суммарный размер всех файлов без чтения медиа...",
                     "Counting files and total size without reading media..."),
    "bt.inventory_result": ("Исходных файлов: {count} Объём (байт): {size}", "Source files: {count} Size (bytes): {size}"),
    "bt.manifest_exists": ("В наборе уже есть готовый manifest. Для нового набора укажи другой каталог.",
                           "The bundle already has a finished manifest. Use another folder for a new bundle."),
    "bt.partial_db": ("В наборе уже есть частично обработанная база. Не перезаписывай её автоматически.",
                      "The bundle already has a partly processed database. It will not be overwritten automatically."),
    "bt.db_no_password": ("В существующей базе нет пароля. Проверь незавершённую сборку.",
                          "The existing database has no password. Inspect the unfinished build."),
    "bt.indexing": ("Индексирую сообщения потоково (оригинальные фото/видео не перекодируются)...",
                    "Indexing messages as a stream (original photos and videos are not re-encoded)..."),
    "bt.expect_chats": ("Проверка отчёта: ожидалось {expected} записей чатов, получено {actual}. Не загружай этот пакет.",
                        "Report check: expected {expected} chat records, got {actual}. Do not upload this bundle."),
    "bt.expect_messages": ("Проверка отчёта: ожидалось {expected} сообщений, получено {actual}. Не загружай этот пакет.",
                           "Report check: expected {expected} messages, got {actual}. Do not upload this bundle."),
    "bt.indexing_contacts": ("Индексирую контакты (без медиа)...", "Indexing contacts (no media)..."),
    "bt.done": ("\nГОТОВО. Теперь загрузи ВЕСЬ каталог набора на Linux VPS.",
                "\nDONE. Now upload the WHOLE bundle folder to the Linux VPS."),
    "bt.done_stats": ("Уникальных чатов: {chats} Сообщений: {messages} Медиа: {media}",
                      "Unique chats: {chats} Messages: {messages} Media: {media}"),
    "bt.done_chats": ("Записей чатов JSON: {chats} (покинутых: {left})", "JSON chat records: {chats} (left: {left})"),
    "bt.done_media": ("Медиа-ссылок: {refs} файлов найдено: {present} отсутствуют: {missing}",
                      "Media references: {refs} files found: {present} missing: {missing}"),
    "bt.media_missing": ("ВНИМАНИЕ: часть путей из result.json не найдена на диске. "
                         "Это могут быть невыгруженные вложения: проверь настройки экспорта.",
                         "WARNING: some paths from result.json are not on disk. "
                         "These may be attachments that were not exported; check the export settings."),
    "bt.folder": ("Каталог: {path}", "Folder: {path}"),
    "bt.build_failed": ("Сборка не завершена: НЕ загружай этот набор. Создай новый чистый каталог.",
                        "The build did not finish: do NOT upload this bundle. Create a new clean folder."),
    # bundletool: verify / activate / pack
    "bt.no_manifest": ("Нет bundle-manifest.json. Сборка не завершена или переданы не все файлы.",
                       "bundle-manifest.json is missing. The build did not finish or not all files were transferred."),
    "bt.unknown_version": ("Неизвестная версия переносимого набора.", "Unknown portable bundle version."),
    "bt.bad_manifest_path": ("В manifest некорректный путь экспорта.", "The manifest has an invalid export path."),
    "bt.sha_checking": ("Проверяю SHA256 исходного result.json (может занять время)...",
                        "Checking the SHA256 of the original result.json (this may take a while)..."),
    "bt.sha_mismatch": ("SHA256 result.json не совпадает: файл изменён или передан не полностью.",
                        "result.json SHA256 mismatch: the file was changed or not fully transferred."),
    "bt.inventory_checking": ("Проверяю полный список файлов по числу и объёму...", "Checking the file count and total size..."),
    "bt.inventory_mismatch": ("Неполная передача файлов: ожидалось {expected}, получено {actual}",
                              "Incomplete file transfer: expected {expected}, got {actual}"),
    "bt.sqlite_error": ("Ошибка базы SQLite: {error}", "SQLite database error: {error}"),
    "bt.bad_portable_ref": ("Некорректная переносимая ссылка в SQLite", "Invalid portable reference in SQLite"),
    "bt.import_outside_bundle": ("SQLite импорт ссылается за пределы набора: {root}", "A SQLite import points outside the bundle: {root}"),
    "bt.media_checking": ("Проверяю наличие КАЖДОГО медиафайла (на большом экспорте это может быть долго)...",
                          "Checking that EVERY media file exists (this can take a while for a large export)..."),
    "bt.media_not_found": ("Не найдены медиа (примеры): {examples}", "Media files not found (examples): {examples}"),
    "bt.media_seen": ("Файлов, упомянутых в SQLite: {count}", "Files referenced in SQLite: {count}"),
    "bt.media_first100": ("Не найден один из первых 100 медиа: {examples}", "One of the first 100 media files is missing: {examples}"),
    "bt.verified": ("Проверка пройдена.", "Verification passed."),
    "bt.suspicious_ref": ("Подозрительная ссылка в SQLite: {ref}", "Suspicious reference in SQLite: {ref}"),
    "bt.export_escapes": ("Путь экспорта выходит за пределы набора: {path}", "The export path leaves the bundle: {path}"),
    "bt.unexpected_ref": ("Неожиданная ссылка на экспорт за пределами пакета: {ref}", "Unexpected export reference outside the bundle: {ref}"),
    "bt.activated": ("SQLite пути привязаны к серверу. Пароль и полнотекстовый индекс сохранены.",
                     "SQLite paths now point to this server. The password and full-text index are kept."),
    "bt.tar_inside": ("Нельзя создавать .tar ВНУТРИ упаковываемого каталога.", "The .tar cannot be created INSIDE the folder being packed."),
    "bt.file_exists": ("Файл уже существует: {path}", "The file already exists: {path}"),
    "bt.packing": ("Создаю один TAR без сжатия: медиа уже сжаты. Нужно дополнительное место размером с весь набор.",
                   "Creating one uncompressed TAR (media are already compressed). Free space the size of the bundle is needed."),
    "bt.packed": ("ГОТОВО, однофайловый набор: {path}", "DONE, single-file bundle: {path}"),
    "bt.bad_export_name": ("Имя экспорта должно быть простым именем папки.", "The export name must be a plain folder name."),
    # bundletool: argparse help
    "bt.help": ("Переносимый Telegram Archive (без Docker)", "Portable Telegram Archive (no Docker)"),
    "bt.help_prepare": ("На Windows собери переносимую папку", "Build the portable folder (on Windows)"),
    "bt.help_export": ("Каталог с result.json и всеми медиа", "Folder with result.json and all media"),
    "bt.help_bundle": ("Папка готового набора", "Ready bundle folder"),
    "bt.help_export_name": ("Имя новой папки под exports/", "Name of the new folder under exports/"),
    "bt.help_copy": ("КОПИРОВАТЬ экспорт, если он лежит отдельно (нужно столько же места)",
                     "COPY the export if it lives elsewhere (needs as much space again)"),
    "bt.help_expect_chats": ("Ожидаемое точное число записей chats.list + left_chats.list из отчёта",
                             "Expected exact number of chats.list + left_chats.list records from the report"),
    "bt.help_expect_messages": ("Ожидаемое точное число сообщений из отчёта", "Expected exact number of messages from the report"),
    "bt.help_verify": ("Проверить переносимый набор до/после передачи", "Verify the portable bundle before/after transfer"),
    "bt.help_full": ("Проверить наличие всех медиа (медленно)", "Check that every media file exists (slow)"),
    "bt.help_activate": ("Привязать SQLite к путям Linux после загрузки", "Bind SQLite to Linux paths after upload"),
    "bt.help_pack": ("Необязательно: записать весь готовый набор в один .tar", "Optional: write the whole ready bundle into one .tar"),
    "bt.help_output": ("Путь вне bundle; нужно место размером с весь набор", "Path outside the bundle; needs space the size of the bundle"),
    "bt.help_preflight": ("Проверить/установить пароль ДО перемещения экспорта", "Check/set the password BEFORE moving the export"),
    "bt.help_gui": ("Окна с поддержкой Ctrl+V (Windows)", "Dialog windows with Ctrl+V support (Windows)"),
    "bt.help_reset": ("Сменить пароль без повторного импорта", "Change the password without re-importing"),
}
