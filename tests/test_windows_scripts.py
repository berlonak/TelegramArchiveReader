# copyright by berlonak
# telegram: @Kilax123
"""Static checks for Windows scripts, which cannot be executed in CI.

cmd.exe decodes each batch line with the current console code page, so Cyrillic text is only
safe after "chcp 65001", and message arguments must avoid characters cmd treats specially.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
BATCH = sorted(ROOT.glob('*.bat'))
POWERSHELL = sorted(ROOT.glob('*.ps1'))
SAY = re.compile(r'^call :say "([^"]*)" "([^"]*)"$')


@pytest.mark.parametrize('path', BATCH, ids=lambda p: p.name)
def test_batch_file_encoding_and_messages(path):
    raw = path.read_bytes()
    assert not raw.startswith(b'\xef\xbb\xbf'), 'a BOM breaks the first "@echo off" line'
    assert b'\n' not in raw.replace(b'\r\n', b''), 'batch files need CRLF line endings'
    lines = raw.decode('utf-8').split('\r\n')
    switched = False
    for number, line in enumerate(lines, 1):
        if line.strip().lower().startswith('chcp 65001'):
            switched = True
        if line.isascii():
            continue
        assert switched, f'line {number}: non-ASCII text before "chcp 65001"'
        match = SAY.match(line.strip())
        assert match, f'line {number}: non-ASCII text outside of call :say'
        russian, english = match.groups()
        assert re.search('[А-Яа-яЁё]', russian) and english.isascii(), f'line {number}'
        for text in (russian, english):
            assert not set(text) & set('&|<>^%"'), f'line {number}: special character in message'


@pytest.mark.parametrize('path', BATCH, ids=lambda p: p.name)
def test_batch_jump_targets_exist(path):
    text = path.read_text(encoding='utf-8')
    labels = {m.lower() for m in re.findall(r'^:(\w+)', text, flags=re.M)}
    targets = {m.lower() for m in re.findall(r'\b(?:goto|call) :?(\w+)', text, flags=re.I)}
    targets -= {'eof'}
    assert targets <= labels, sorted(targets - labels)


@pytest.mark.parametrize('path', POWERSHELL, ids=lambda p: p.name)
def test_powershell_scripts_have_bom_and_no_ps7_only_syntax(path):
    raw = path.read_bytes()
    # Windows PowerShell 5.1 reads BOM-less files as ANSI and garbles Cyrillic.
    assert raw.startswith(b'\xef\xbb\xbf')
    text = raw.decode('utf-8-sig')
    assert '??' not in text and not re.search(r'\)\s*(&&|\|\|)', text)
    if re.search('[А-Яа-яЁё]', text):
        assert 'function T(' in text


def test_lock_prompt_is_in_powershell_not_batch():
    assert 'set /p' not in (ROOT / 'CHECK-LOCK.bat').read_text(encoding='utf-8')
