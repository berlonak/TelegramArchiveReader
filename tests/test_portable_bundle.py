# copyright by berlonak
# telegram: @Kilax123
"""Portable paths, media presence and re-activation (tiny fixture, not a large-export stress test)."""
from __future__ import annotations

import shutil
import sqlite3
import sys
import types
from pathlib import Path

import bundletool
import tgarchive.importer as importer


def test_portable_bundle_survives_move(tmp_path, monkeypatch):
    # The small fixture uses importer JSON fallback so CI needn't install ijson.
    # In production prepare() insists ijson be installed for streaming large JSON.
    monkeypatch.setitem(sys.modules, "ijson", types.ModuleType("ijson"))
    monkeypatch.setattr(importer, "ijson", None)
    monkeypatch.setattr(bundletool.getpass, "getpass", lambda prompt: "strong-private-test-password")

    bundle = tmp_path / "windows-ready"
    export = bundle / "exports" / "first-export"
    fixture = Path(__file__).resolve().parents[1] / "examples" / "demo-export"
    shutil.copytree(fixture, export)
    args = types.SimpleNamespace(bundle=str(bundle), export=str(export), copy_export=False,
                                 export_name="first-export")
    bundletool.prepare(args)
    bundletool.verify(bundle, full=True)
    with sqlite3.connect(bundle / "data" / "archive.sqlite3") as conn:
        (root,) = conn.execute("SELECT root FROM imports").fetchone()
        assert root.startswith(bundletool.TOKEN)
        (password,) = conn.execute("SELECT value FROM config WHERE name='password_hash'").fetchone()
        assert password.startswith("$argon2id$")

    remote = tmp_path / "linux-ready"
    shutil.move(str(bundle), str(remote))
    bundletool.verify(remote, full=True)
    bundletool.activate(remote)
    bundletool.verify(remote, full=True)
    with sqlite3.connect(remote / "data" / "archive.sqlite3") as conn:
        (root,) = conn.execute("SELECT root FROM imports").fetchone()
        assert root == str(remote / "exports" / "first-export")
        assert conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0] > 10
        assert conn.execute("SELECT COUNT(*) FROM media").fetchone()[0] > 0
