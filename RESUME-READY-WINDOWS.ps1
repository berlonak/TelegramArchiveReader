# copyright by berlonak
# telegram: @Kilax123
# Resume only if the ORIGINAL EXPORT has already been staged in ready/exports/first-export.
# Refuse to overwrite any partially imported database or completed archive.
param([string]$BundlePath = '')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not $BundlePath) { $BundlePath = Read-Host 'Full path to an INCOMPLETE TelegramArchive-ready folder' }
$BundlePath = [IO.Path]::GetFullPath($BundlePath.Trim('"').Trim("'"))
$export = Join-Path (Join-Path $BundlePath 'exports') 'first-export'
if (Test-Path -LiteralPath (Join-Path $BundlePath 'bundle-manifest.json')) {
  throw 'This archive is already complete. Use START-LOCAL.bat or RESET-PASSWORD.bat instead.'
}
if (-not (Test-Path -LiteralPath (Join-Path $export 'result.json') -PathType Leaf)) {
  throw "Staged result.json NOT found: $export. Do not use RESUME; inspect source and ready folders."
}
$original = Read-Host 'FULL path to the ORIGINAL export folder, BEFORE the move (to detect split move)'
if (-not $original) { throw 'Original source path is required. No data was modified.' }
$original = [IO.Path]::GetFullPath($original.Trim('"').Trim("'"))
if (Test-Path -LiteralPath $original -PathType Container) {
  $leftovers = @(Get-ChildItem -LiteralPath $original -Force | Select-Object -First 1)
  if ($leftovers.Count -gt 0) {
    throw "The ORIGINAL folder still contains files: $original. The export might have been split by a failed move. Compare folders before resuming; do not delete either."
  }
}
Write-Host 'Resuming an INCOMPLETE staged build. Original media will not be moved or re-copied.' -ForegroundColor Cyan
py -3 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Python 3.10+ is required.' }
& .\.venv\Scripts\python.exe -m pip install -e .
if ($LASTEXITCODE -ne 0) { throw 'Dependencies installation failed.' }
& .\.venv\Scripts\python.exe bundletool.py preflight-password --bundle $BundlePath --gui
if ($LASTEXITCODE -ne 0) { throw 'Existing DB contains imported data or password dialog was cancelled. Nothing was deleted.' }
& .\.venv\Scripts\python.exe bundletool.py prepare --export $export --bundle $BundlePath
if ($LASTEXITCODE -ne 0) { throw 'Build not finished. Keep the export and DB intact for diagnosis.' }
& .\.venv\Scripts\python.exe bundletool.py verify --bundle $BundlePath --full
if ($LASTEXITCODE -ne 0) { throw 'Verification failed. Do not upload to server.' }
Write-Host "DONE: $BundlePath" -ForegroundColor Green
