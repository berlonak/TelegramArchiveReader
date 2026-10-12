# Contributing

Thanks for your interest in Telegram Archive Reader!

## Never share real data

Do **not** attach your Telegram export, `result.json`, `archive.sqlite3`, screenshots of real
chats, or a `TelegramArchive-ready` folder to issues or pull requests. Reproduce problems with
the synthetic export in `examples/demo-export/` or a small fictional one.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
python -m pytest -q tests
```

Run the app against the demo data:

```bash
tgarchive init
tgarchive import examples/demo-export
tgarchive serve
```

## Pull requests

- Keep changes focused and add a test for every bug fix.
- Keep the security properties intact: localhost binding, Origin checks, path validation,
  authenticated media.
- Behaviour that moves or deletes user files must stay explicit and confirmable.

## Adding a language

All web UI strings live in [`tgarchive/static/i18n.js`](tgarchive/static/i18n.js). Copy the `en`
block under a new language code, translate the values, add the code to `LANGS`, and run
`python -m pytest tests/test_i18n.py`: it checks that every key exists in every dictionary.

## Ideas that would help

- More UI languages (see above), and English messages for the CLI and Windows scripts.
- More Telegram export edge cases as synthetic test fixtures.
