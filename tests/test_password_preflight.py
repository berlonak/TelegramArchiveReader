# copyright by berlonak
# telegram: @Kilax123
"""Exercise recovery paths with *synthetic* data; not a Windows lock stress test."""
from pathlib import Path
import shutil
import sqlite3
import sys
import types

import pytest
from argon2 import PasswordHasher
import bundletool
import tgarchive.importer as importer


def test_preflight_password_before_moving_then_prepare_and_reset(tmp_path, monkeypatch):
    bundle = tmp_path / 'ready'
    entry = bundle / 'exports' / 'first-export'
    monkeypatch.setattr(bundletool.getpass, 'getpass', lambda prompt: 'first-correct-password-2026')
    bundletool.preflight_password(bundle, gui=False)
    assert not entry.exists()  # Password checked before touching a source export.
    stub = bundle / 'data' / 'archive.sqlite3'
    with sqlite3.connect(stub) as con:
        digest = con.execute("SELECT value FROM config WHERE name='password_hash'").fetchone()[0]
        assert PasswordHasher().verify(digest, 'first-correct-password-2026')

    fixture = Path(__file__).resolve().parents[1] / 'examples' / 'demo-export'
    shutil.copytree(fixture, entry)
    monkeypatch.setitem(sys.modules, 'ijson', types.ModuleType('ijson'))
    monkeypatch.setattr(importer, 'ijson', None)
    args = types.SimpleNamespace(bundle=str(bundle), export=str(entry),
                                 copy_export=False, export_name='first-export')
    bundletool.prepare(args)
    bundletool.verify(bundle, full=True)
    with sqlite3.connect(stub) as con:
        assert con.execute('SELECT COUNT(*) FROM messages').fetchone()[0] == 90

    monkeypatch.setattr(bundletool.getpass, 'getpass', lambda prompt: 'second-correct-password-2026')
    bundletool.reset_password(bundle, gui=False)
    with sqlite3.connect(stub) as con:
        digest = con.execute("SELECT value FROM config WHERE name='password_hash'").fetchone()[0]
        assert PasswordHasher().verify(digest, 'second-correct-password-2026')
        with pytest.raises(Exception):
            PasswordHasher().verify(digest, 'first-correct-password-2026')
        assert con.execute('SELECT COUNT(*) FROM messages').fetchone()[0] == 90
    bundletool.verify(bundle, full=True)


def test_preflight_reuses_safe_stub_but_rejects_partially_imported_db(tmp_path, monkeypatch):
    monkeypatch.setenv('TGARCHIVE_LANG', 'ru')
    bundle = tmp_path / 'ready'
    values = iter(('first-long-enough-2026', 'first-long-enough-2026',
                   'second-long-enough-2026', 'second-long-enough-2026'))
    monkeypatch.setattr(bundletool.getpass, 'getpass', lambda prompt: next(values))
    bundletool.preflight_password(bundle, gui=False)
    bundletool.preflight_password(bundle, gui=False)
    with sqlite3.connect(bundle / 'data' / 'archive.sqlite3') as con:
        hash_ = con.execute("SELECT value FROM config WHERE name='password_hash'").fetchone()[0]
        assert PasswordHasher().verify(hash_, 'second-long-enough-2026')
        con.execute('INSERT INTO imports(root,source_file,imported_at,messages_seen) VALUES(?,?,?,?)',
                    ('somewhere', 'somewhere/result.json', 123, 0))
    with pytest.raises(SystemExit, match='незавершённая база'):
        bundletool.preflight_password(bundle, gui=False)
