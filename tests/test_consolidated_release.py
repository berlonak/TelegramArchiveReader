# copyright by berlonak
# telegram: @Kilax123
"""Smoke check that clean Windows builder includes the local runner and current hotfix."""
import importlib.util
import json
import shutil
import sys
import types
from pathlib import Path

from fastapi.testclient import TestClient
import bundletool
import tgarchive.importer as importer
from tgarchive.app import PASS_HASHER, app
from tgarchive.db import connect


def test_complete_builder_creates_immediately_local_runnable_bundle(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "ijson", types.ModuleType("ijson"))
    monkeypatch.setattr(importer, "ijson", None)  # tiny, entirely synthetic fixture
    monkeypatch.setattr(bundletool.getpass, "getpass", lambda prompt: "sample-pass-not-real-2026")
    bundle = tmp_path / "new bundle"
    export = bundle / "exports" / "first-export"
    shutil.copytree(Path(__file__).resolve().parents[1]/"examples"/"demo-export",export)
    args=types.SimpleNamespace(bundle=str(bundle),export=str(export),copy_export=False,export_name="first-export")
    bundletool.prepare(args)
    assert (bundle/"START-LOCAL.bat").is_file()
    assert (bundle/"start-local.py").is_file()
    assert (bundle/"RESET-PASSWORD.bat").is_file()
    assert (bundle/"SERVER-RU.md").is_file()
    assert (bundle/"SERVER.md").is_file()
    assert (bundle/"deploy"/"docker"/"compose.yaml").is_file()
    assert json.loads((bundle/"bundle-manifest.json").read_text())["app_version"] == "0.5.0"
    bundletool.verify(bundle,full=True)
    moved=tmp_path/"moved bundle"
    shutil.move(bundle,moved)
    monkeypatch.setenv("TGARCHIVE_DATA_DIR",str(moved/"data"))
    monkeypatch.setenv("TGARCHIVE_BUNDLE_ROOT",str(moved))
    spec=importlib.util.spec_from_file_location("local_launcher", moved/"start-local.py")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.preflight()
    with TestClient(app) as client:
        assert client.get("/api/media/1").status_code == 401
        assert client.post("/api/auth/login",json={"password":"sample-pass-not-real-2026"}).status_code==200
        items=client.get("/api/gallery?kind=photo").json()["items"]
        assert items
        url=items[0]["url"]
        assert client.get(url).status_code == 200
    assert "Где старые переписки?" not in (moved/"app"/"tgarchive"/"static"/"index.html").read_text()
