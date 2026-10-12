# copyright by berlonak
# telegram: @Kilax123
"""Run the Windows scripts' safe branches on a real Windows host (CI: windows-latest).

Only paths that stop before touching any data are exercised: missing bundle, missing export,
wrong confirmation word. Output is checked for the English texts; Russian runs check that the
script takes the same path (exit code) and prints Cyrillic when the stream encoding allows it.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform != 'win32', reason='needs cmd.exe and Windows PowerShell')
ROOT = Path(__file__).parents[1]


def run(command, lang, cwd, stdin=''):
    env = {**os.environ, 'TGARCHIVE_LANG': lang}
    result = subprocess.run(command, cwd=cwd, env=env, input=stdin.encode('utf-8'),
                            capture_output=True, timeout=180)
    output = (result.stdout + result.stderr).decode('utf-8', errors='replace')
    return result.returncode, output


def powershell(script, *args):
    return ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(ROOT / script), *args]


def test_windows_powershell_5_parses_every_script():
    check = ("$bad = 0; foreach ($f in Get-ChildItem -LiteralPath '{root}' -Filter *.ps1) {{ "
             "$t = $null; $e = $null; [void][System.Management.Automation.Language.Parser]::ParseFile($f.FullName, [ref]$t, [ref]$e); "
             "foreach ($x in $e) {{ $bad++; Write-Output ($f.Name + ':' + $x.Extent.StartLineNumber + ' ' + $x.Message) }} }}; "
             "Write-Output ('PSVersion ' + $PSVersionTable.PSVersion); exit $bad").format(root=ROOT)
    result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', check], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'PSVersion 5.' in result.stdout


@pytest.mark.parametrize('lang, expected', [('en', 'ERROR: Put BOTH launch files'), ('ru', 'ОШИБКА: положи ОБА файла')])
def test_start_local_bat_reports_missing_bundle(tmp_path, lang, expected):
    shutil.copy2(ROOT / 'START-LOCAL.bat', tmp_path / 'START-LOCAL.bat')
    code, output = run(['cmd.exe', '/d', '/c', 'START-LOCAL.bat'], lang, tmp_path)
    assert code == 1, output
    assert expected in output, output


@pytest.mark.parametrize('lang, expected', [('en', 'Run this file from inside a completed'), ('ru', 'Запусти этот файл из готовой папки')])
def test_reset_password_bat_reports_missing_bundle(tmp_path, lang, expected):
    shutil.copy2(ROOT / 'RESET-PASSWORD.bat', tmp_path / 'RESET-PASSWORD.bat')
    code, output = run(['cmd.exe', '/d', '/c', 'RESET-PASSWORD.bat'], lang, tmp_path)
    assert code == 1, output
    assert expected in output, output


@pytest.mark.parametrize('lang', ['en', 'ru'])
def test_check_lock_reports_missing_folder(tmp_path, lang):
    code, output = run(powershell('CHECK-LOCK-WINDOWS.ps1', '-ExportPath', str(tmp_path / 'missing'), '-Lang', lang), lang, tmp_path)
    assert code == 2, output
    if lang == 'en':
        assert 'Directory no longer exists' in output, output


@pytest.mark.parametrize('lang', ['en', 'ru'])
def test_builder_stops_without_result_json(tmp_path, lang):
    (tmp_path / 'empty').mkdir()
    code, output = run(powershell('build-one-folder-windows.ps1', '-ExportPath', str(tmp_path / 'empty')), lang, tmp_path)
    assert code == 1, output
    if lang == 'en':
        assert 'BUILD FAILED' in output and 'result.json not found' in output, output


def test_builder_wrong_confirmation_word_moves_nothing(tmp_path):
    export = tmp_path / 'export'
    export.mkdir()
    (export / 'result.json').write_text('{}', encoding='utf-8')
    code, output = run(powershell('build-one-folder-windows.ps1', '-ExportPath', str(export),
                                  '-BundlePath', str(tmp_path / 'ready')), 'en', tmp_path, stdin='nope\n')
    assert code == 1, output
    assert 'To confirm, type MOVE' in output and 'Cancelled' in output, output
    assert (export / 'result.json').is_file() and not (tmp_path / 'ready').exists()


@pytest.mark.parametrize('lang, expected', [('en', 'bundle-manifest.json is missing'), ('ru', 'Нет bundle-manifest.json')])
def test_bundletool_messages_on_windows(tmp_path, lang, expected):
    env = {**os.environ, 'TGARCHIVE_LANG': lang, 'PYTHONUTF8': '1'}
    result = subprocess.run([sys.executable, str(ROOT / 'bundletool.py'), 'verify', '--bundle', str(tmp_path)],
                            capture_output=True, env=env, timeout=60)
    assert result.returncode == 1
    assert expected in result.stderr.decode('utf-8'), result.stderr


def test_language_detection_uses_windows_ui_language(monkeypatch):
    from tgarchive.messages import language
    monkeypatch.delenv('TGARCHIVE_LANG', raising=False)
    assert language() in ('ru', 'en')
