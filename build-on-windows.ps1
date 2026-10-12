# copyright by berlonak
# telegram: @Kilax123
# Optional helper. Run inside an already-extracted telegram-archive source folder.
param(
  [Parameter(Mandatory=$true)][string]$ExportPath,
  [Parameter(Mandatory=$true)][string]$BundlePath,
  [switch]$CopyExport
)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path -LiteralPath $ExportPath -PathType Container)) { throw "Export folder not found: $ExportPath" }
py -3 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "Python 3.10+ not found. Install Python and retry." }
& .\.venv\Scripts\python.exe -m pip install -e .
if ($LASTEXITCODE -ne 0) { throw "Failed to install Python dependencies" }
$params = @('bundletool.py', 'prepare', '--export', $ExportPath, '--bundle', $BundlePath)
if ($CopyExport) { $params += '--copy-export' }
& .\.venv\Scripts\python.exe @params
if ($LASTEXITCODE -ne 0) { throw "Bundle preparation failed" }
& .\.venv\Scripts\python.exe .\bundletool.py verify --bundle $BundlePath --full
if ($LASTEXITCODE -ne 0) { throw "Bundle verification failed" }
Write-Host "Package is ready: $BundlePath" -ForegroundColor Green
