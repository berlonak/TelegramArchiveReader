# TelegramArchive-ready — portable ready bundle / готовый переносимый пакет

**English** · [Русский ниже](#русский)

This bundle was created for a private, read-only Telegram reader and contains **personal** data: the message index, an Argon2id password hash, the original JSON, photos, videos and attachments. **Do not send this folder to strangers and do not publish it.**

- Windows: `START-LOCAL.bat` → local address `http://127.0.0.1:8000`. Stop with `Ctrl+C`.
- Moving to Linux: stop the local server completely, check the JSON checksum and the files with `bundletool.py verify --bundle <PATH> --full`, and transfer the **whole folder** over SFTP.
- Linux: see the full guide in `SERVER.md`. On a clean Ubuntu/Debian: `sudo bash /srv/tgarchive/deploy/install-bundle.sh PUBLIC_IP EMAIL` **after** placing and verifying the bundle.
- The `.venv` is not transferred between Windows and Linux: the scripts install system-compatible dependencies into a separate environment. Private media are stored separately from SQLite and are not duplicated.
- **This folder is NOT a Docker container** but a portable pre-indexed snapshot. A separate Docker Compose template is in `deploy/docker/compose.yaml`.
- Messages are in Russian or English depending on the system language; set `TGARCHIVE_LANG=ru` or `en` to choose.

## Русский

Пакет создан для личной read-only читалки Telegram и содержит **личные** данные: индекс сообщений, Argon2id-хеш пароля, исходный JSON, фото, видео и вложения. **Не пересылай эту папку незнакомым людям и не публикуй.**

- Windows: `START-LOCAL.bat` → локальный адрес `http://127.0.0.1:8000`. Остановить `Ctrl+C`.
- Передача на Linux: полностью останови локальный сервер, проверь контрольную сумму JSON и файлы командой `bundletool.py verify --bundle <ПУТЬ> --full` и переноси **всю папку** через SFTP.
- Linux: полное руководство `SERVER-RU.md`. Для чистого Ubuntu/Debian: `sudo bash /srv/tgarchive/deploy/install-bundle.sh ПУБЛИЧНЫЙ_IP EMAIL` **после** размещения и проверки пакета.
- `.venv` на Windows/Linux не переносится: скрипты автоматически установят системно-совместимые зависимости в отдельное окружение. Приватные медиа лежат отдельно от SQLite и не удваиваются.
- **Этот каталог — НЕ Docker-контейнер**, а портативный pre-indexed snapshot. Отдельный Docker Compose шаблон лежит в `deploy/docker/compose.yaml`.
- Сообщения выводятся на русском или английском в зависимости от языка системы; выбрать явно: `TGARCHIVE_LANG=ru` или `en`.
