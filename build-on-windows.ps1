# copyright by berlonak
# telegram: @Kilax123
# Optional helper. Run inside an already-extracted telegram-archive source folder.
param(
  [Parameter(Mandatory=$true)][string]$ExportPath,
  [Parameter(Mandatory=$true)][string]$BundlePath,
  [switch]$CopyExport
)
$ErrorActionPreference = 'Stop'
# Messages follow TGARCHIVE_LANG (ru/en), otherwise the Windows display language.
$TgLang = if (@('ru', 'en') -contains "$env:TGARCHIVE_LANG".ToLowerInvariant()) { "$env:TGARCHIVE_LANG".ToLowerInvariant() }
          elseif (@('ru', 'uk', 'be', 'kk') -contains (Get-UICulture).TwoLetterISOLanguageName) { 'ru' } else { 'en' }
$env:TGARCHIVE_LANG = $TgLang
function T([string]$Ru, [string]$En) { if ($TgLang -eq 'ru') { $Ru } else { $En } }
Set-Location $PSScriptRoot
if (-not (Test-Path -LiteralPath $ExportPath -PathType Container)) { throw (T "Папка экспорта не найдена: $ExportPath" "Export folder not found: $ExportPath") }
py -3 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw (T 'Python 3.10+ не найден. Установи Python и повтори.' 'Python 3.10+ not found. Install Python and retry.') }
& .\.venv\Scripts\python.exe -m pip install -e .
if ($LASTEXITCODE -ne 0) { throw (T 'Не удалось установить зависимости Python' 'Failed to install Python dependencies') }
$params = @('bundletool.py', 'prepare', '--export', $ExportPath, '--bundle', $BundlePath)
if ($CopyExport) { $params += '--copy-export' }
& .\.venv\Scripts\python.exe @params
if ($LASTEXITCODE -ne 0) { throw (T 'Подготовка пакета не удалась' 'Bundle preparation failed') }
& .\.venv\Scripts\python.exe .\bundletool.py verify --bundle $BundlePath --full
if ($LASTEXITCODE -ne 0) { throw (T 'Проверка пакета не пройдена' 'Bundle verification failed') }
Write-Host (T "Пакет готов: $BundlePath" "Package is ready: $BundlePath") -ForegroundColor Green
