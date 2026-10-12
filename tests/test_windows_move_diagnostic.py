# copyright by berlonak
# telegram: @Kilax123
from pathlib import Path

ROOT = Path(__file__).parents[1]

def test_original_move_flow_kept():
    script = (ROOT / "build-one-folder-windows.ps1").read_text(encoding="utf-8-sig")
    assert "Move-Item -LiteralPath $export -Destination $expectedExport" in script
    assert "CHECK-LOCK-WINDOWS.ps1" in script
    assert "stage-export" not in script

def test_lock_helper_only_runs_signed_microsoft_binary_with_consent():
    helper = (ROOT / "CHECK-LOCK-WINDOWS.ps1").read_text(encoding="utf-8-sig")
    assert "Read-Host 'Download and use official Microsoft Handle.zip now? Enter YES'" in helper
    assert "download.sysinternals.com/files/Handle.zip" in helper
    assert "Get-AuthenticodeSignature" in helper
    assert "-Verb RunAs" in helper
    assert "-accepteula" in helper
    assert "Close-Handle" not in helper
