# Security Policy

This app serves private correspondence, so security reports are very welcome.

## Supported versions

Only the latest release receives fixes.

## Reporting a vulnerability

Please do **not** open a public issue. Use GitHub's
[private vulnerability reporting](https://github.com/berlonak/TelegramArchiveReader/security/advisories/new)
or contact the maintainer on Telegram: @Kilax123.

Include steps to reproduce with synthetic data only. Never send real exports or databases.

## Scope notes

- The password and HTTPS protect web access; files on disk are not encrypted by this project.
- The app is designed to listen on `127.0.0.1` behind nginx. Exposing port 8000 directly is
  not a supported configuration.
