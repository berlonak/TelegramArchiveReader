# copyright by berlonak
# telegram: @Kilax123
"""Console messages exist in both languages and the language is chosen predictably."""
import re
import sys

import pytest

from tgarchive import messages
from tgarchive.messages import MESSAGES, language, msg


def test_every_message_has_both_languages_with_same_placeholders():
    for key, (ru, en) in MESSAGES.items():
        assert ru.strip() and en.strip(), key
        assert set(re.findall(r'\{(\w+)\}', ru)) == set(re.findall(r'\{(\w+)\}', en)), key
        assert not re.search('[А-Яа-яЁё]', en), key


def test_every_message_key_used_in_code_exists():
    from pathlib import Path
    root = Path(__file__).parents[1]
    used = set()
    for path in [root / 'bundletool.py', root / 'start-local.py', *(root / 'tgarchive').glob('*.py')]:
        used |= set(re.findall(r'\bmsg\("([\w.]+)"', path.read_text(encoding='utf-8')))
    assert used and used <= set(MESSAGES), sorted(used - set(MESSAGES))


@pytest.mark.parametrize('env, expected', [
    ({'TGARCHIVE_LANG': 'ru', 'LANG': 'en_US.UTF-8'}, 'ru'),
    ({'TGARCHIVE_LANG': 'EN', 'LANG': 'ru_RU.UTF-8'}, 'en'),
    ({'LANG': 'ru_RU.UTF-8'}, 'ru'),
    ({'LANG': 'uk_UA.UTF-8'}, 'ru'),
    ({'LC_ALL': 'de_DE.UTF-8', 'LANG': 'ru_RU.UTF-8'}, 'en'),
    ({'LANG': 'C.UTF-8'}, 'en'),
    ({}, 'en'),
])
def test_language_selection(monkeypatch, env, expected):
    monkeypatch.setattr(sys, 'platform', 'linux')
    for name in ('TGARCHIVE_LANG', 'LC_ALL', 'LC_MESSAGES', 'LANG'):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    assert language() == expected


def test_msg_formats_in_selected_language(monkeypatch):
    monkeypatch.setenv('TGARCHIVE_LANG', 'en')
    assert msg('bt.dest_exists', path='/x') == 'The destination folder already exists: /x'
    monkeypatch.setenv('TGARCHIVE_LANG', 'ru')
    assert msg('bt.dest_exists', path='/x') == 'Папка назначения уже есть: /x'
    assert messages.msg('error', message='x') == 'Ошибка: x'


def test_bundletool_help_in_english(monkeypatch, capsys):
    monkeypatch.setenv('TGARCHIVE_LANG', 'en')
    import bundletool
    monkeypatch.setattr(sys, 'argv', ['bundletool.py', '--help'])
    with pytest.raises(SystemExit):
        bundletool.main()
    out = capsys.readouterr().out
    assert 'Build the portable folder' in out and not re.search('[А-Яа-яЁё]', out)
