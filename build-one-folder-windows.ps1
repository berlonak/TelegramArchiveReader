# copyright by berlonak
# telegram: @Kilax123
# Telegram Archive builder - safe, restartable after an early failed Windows move.
# Password is confirmed in a GUI BEFORE moving or copying the large export.
param(
  [string]$ExportPath = '',
  [string]$BundlePath = '',
  [switch]$CopyExport,
  [switch]$StrictSnapshot,
  [int]$ExpectChatRecords = 0,
  [int]$ExpectMessageRecords = 0
)
$ErrorActionPreference = 'Stop'
# Messages follow TGARCHIVE_LANG (ru/en), otherwise the Windows display language.
$TgLang = if (@('ru', 'en') -contains "$env:TGARCHIVE_LANG".ToLowerInvariant()) { "$env:TGARCHIVE_LANG".ToLowerInvariant() }
          elseif (@('ru', 'uk', 'be', 'kk') -contains (Get-UICulture).TwoLetterISOLanguageName) { 'ru' } else { 'en' }
$env:TGARCHIVE_LANG = $TgLang
function T([string]$Ru, [string]$En) { if ($TgLang -eq 'ru') { $Ru } else { $En } }
trap {
  Write-Host ''
  Write-Host (T 'СБОРКА НЕ ЗАВЕРШЕНА. Причина указана ниже.' 'BUILD FAILED. The reason is shown below.') -ForegroundColor Red
  break
}
Set-Location $PSScriptRoot
if ($StrictSnapshot -and ($ExpectChatRecords -le 0 -or $ExpectMessageRecords -le 0)) {
  throw (T '-StrictSnapshot требует -ExpectChatRecords и -ExpectMessageRecords (числа из отчёта экспорта).' `
           '-StrictSnapshot needs -ExpectChatRecords and -ExpectMessageRecords (numbers from the export report).')
}
if (-not $ExportPath) { $ExportPath = Read-Host (T 'Путь к папке экспорта Telegram (result.json)' 'Path to the Telegram export folder (result.json)') }
$ExportPath = $ExportPath.Trim('"').Trim("'")
$export = (Resolve-Path -LiteralPath $ExportPath -ErrorAction Stop).Path.TrimEnd('\')
if (-not (Test-Path -LiteralPath (Join-Path $export 'result.json') -PathType Leaf)) {
  throw (T "Файл result.json не найден: $export" "result.json not found: $export")
}
if (-not $BundlePath) { $BundlePath = Join-Path (Split-Path $export -Parent) 'TelegramArchive-ready' }
$BundlePath = [IO.Path]::GetFullPath($BundlePath).TrimEnd('\')
$expectedExport = Join-Path (Join-Path $BundlePath 'exports') 'first-export'
if ([IO.Path]::GetPathRoot($export).ToLowerInvariant() -ne [IO.Path]::GetPathRoot($BundlePath).ToLowerInvariant() -and -not $CopyExport) {
  throw (T 'Режим переноса работает только на одном диске. Для другого диска запусти с -CopyExport.' `
           'Move mode only works on one drive. For another drive, run with -CopyExport.')
}
# Exclude source/destination self-nesting, including cases with trailing slashes.
$e = $export.ToLowerInvariant() + '\'
$b = $BundlePath.ToLowerInvariant() + '\'
if ($e.StartsWith($b) -or $b.StartsWith($e)) {
  throw (T 'Экспорт и папка готового архива не должны лежать друг внутри друга.' `
           'The export and the ready archive folder must not be inside each other.')
}
# An old failed v0.3.1 build may have left only ready/exports (empty).
# Never delete, move or overwrite unknown data in a previous ready directory.
if (Test-Path -LiteralPath $BundlePath) {
  if (Test-Path -LiteralPath (Join-Path $BundlePath 'bundle-manifest.json')) {
    throw (T "Готовый пакет уже существует: $BundlePath. Не запускай импорт второй раз. Для смены пароля есть RESET-PASSWORD.bat." `
             "A ready bundle already exists: $BundlePath. Do not run the import twice. Use RESET-PASSWORD.bat to change the password.")
  }
  $allowed = @('exports', 'data')
  $unexpected = @(Get-ChildItem -LiteralPath $BundlePath -Force | Where-Object { $allowed -notcontains $_.Name })
  if ($unexpected.Count -gt 0) {
    throw (T "В $BundlePath лежат файлы незавершённой сборки. Не удаляй их автоматически; проверь содержимое или укажи ДРУГОЙ BundlePath." `
             "$BundlePath contains files from an unfinished build. Do not delete them automatically; inspect them or choose ANOTHER BundlePath.")
  }
  $exportsRoot = Join-Path $BundlePath 'exports'
  if (Test-Path -LiteralPath $exportsRoot) {
    $exportContents = @(Get-ChildItem -LiteralPath $exportsRoot -Force)
    if ($exportContents.Count -gt 0) {
      throw (T "В $exportsRoot уже есть данные. После неудачного переноса файлы могли разделиться между папками. Остановись и проверь обе папки вручную." `
               "$exportsRoot already contains data. After a failed move the files may be split between folders. Stop and check both folders manually.")
    }
  }
  $dataRoot = Join-Path $BundlePath 'data'
  if (Test-Path -LiteralPath $dataRoot) {
    $dataContents = @(Get-ChildItem -LiteralPath $dataRoot -Force | Where-Object {
      $_.Name -notin @('archive.sqlite3', 'archive.sqlite3-wal', 'archive.sqlite3-shm')
    })
    if ($dataContents.Count -gt 0) {
      throw (T "Неожиданные файлы в $dataRoot. Проверь папку перед повторным запуском." `
               "Unexpected files in $dataRoot. Check the folder before running again.")
    }
  }
}
Write-Host ("`n" + (T "Экспорт: $export" "Export: $export")) -ForegroundColor Cyan
Write-Host (T "Готовый пакет: $BundlePath" "Ready bundle: $BundlePath")
$cancelled = T 'Отменено: исходные данные не затронуты.' 'Cancelled: the source data was not touched.'
if ($CopyExport) {
  $word = T 'КОПИРОВАТЬ' 'COPY'
  Write-Host (T 'Выбран режим КОПИРОВАНИЯ. Понадобится дополнительно столько же свободного места, сколько занимает экспорт.' `
                'COPY mode selected. You need as much free space again as the export takes.') -ForegroundColor Yellow
  $confirmation = Read-Host (T "Для подтверждения введи $word" "To confirm, type $word")
  if ($confirmation -cne $word) { throw $cancelled }
} else {
  $word = T 'ПЕРЕМЕСТИТЬ' 'MOVE'
  Write-Host (T "Экспорт будет ПЕРЕМЕЩЁН в $expectedExport (не удалён)." "The export will be MOVED to $expectedExport (not deleted).") -ForegroundColor Yellow
  Write-Host (T 'Закрой Telegram Archive, Python, проводники и редакторы, открывшие экспорт.' `
                'Close Telegram Archive, Python, Explorer windows and editors that have the export open.') -ForegroundColor Yellow
  $confirmation = Read-Host (T "Для подтверждения введи $word" "To confirm, type $word")
  if ($confirmation -cne $word) { throw $cancelled }
}
# Dependencies and password are checked before moving the source directory.
py -3 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw (T 'Нужен Python 3.10+; экспорт не перенесён.' 'Python 3.10+ is required; the export was not moved.') }
& .\.venv\Scripts\python.exe -m pip install -e .
if ($LASTEXITCODE -ne 0) { throw (T 'Не удалось установить библиотеки; экспорт не перенесён.' 'Could not install the libraries; the export was not moved.') }
New-Item -ItemType Directory -Path (Join-Path $BundlePath 'exports') -Force | Out-Null
& .\.venv\Scripts\python.exe bundletool.py preflight-password --bundle $BundlePath --gui
if ($LASTEXITCODE -ne 0) { throw (T 'Пароль не подтверждён. Экспорт остался на месте.' 'The password was not confirmed. The export stayed in place.') }
if (Test-Path -LiteralPath $expectedExport) {
  throw (T "Папка назначения уже существует: $expectedExport. Не перезаписывай старую сборку." `
           "The destination folder already exists: $expectedExport. Do not overwrite an old build.")
}
try {
  if ($CopyExport) {
    Copy-Item -LiteralPath $export -Destination $expectedExport -Recurse -ErrorAction Stop
  } else {
    Move-Item -LiteralPath $export -Destination $expectedExport -ErrorAction Stop
  }
} catch {
  Write-Host ("`n" + (T 'ОШИБКА: Windows не смогла перенести/скопировать папку.' 'ERROR: Windows could not move/copy the folder.')) -ForegroundColor Red
  Write-Host (T 'Закрой START-LOCAL, Python, VS Code, окна Проводника и программы, которые могли открыть экспорт.' `
                'Close START-LOCAL, Python, VS Code, Explorer windows and any program that may have the export open.') -ForegroundColor Yellow
  Write-Host (T "Проверь обе папки: $export  и  $expectedExport" "Check both folders: $export  and  $expectedExport")
  Write-Host (T 'Ничего не удаляй, если файлы оказались в обеих папках.' 'Do not delete anything if files ended up in both folders.') -ForegroundColor Yellow
  Write-Host (T "Причина Windows: $_" "Windows reason: $_") -ForegroundColor Red
  Write-Host ("`n" + (T 'Запускаю диагностику открытых файлов и каталогов...' 'Starting the open files and folders diagnostic...')) -ForegroundColor Yellow
  try {
    & (Join-Path $PSScriptRoot 'CHECK-LOCK-WINDOWS.ps1') -ExportPath $export
  } catch {
    Write-Host (T "Диагностика недоступна: $_" "Diagnostic unavailable: $_") -ForegroundColor Yellow
    Write-Host (T 'Можно отдельно запустить CHECK-LOCK.bat от администратора.' 'You can run CHECK-LOCK.bat as administrator separately.') -ForegroundColor Yellow
  }
  throw (T 'Перемещение не выполнено. Проверь обе папки перед повтором: перенос мог остановиться частично.' `
           'The move did not complete. Check both folders before retrying: it may have stopped halfway.')
}
if (-not (Test-Path -LiteralPath (Join-Path $expectedExport 'result.json'))) {
  throw (T "После переноса result.json отсутствует: $expectedExport. НЕ удаляй исходник." `
           "result.json is missing after the move: $expectedExport. Do NOT delete the source.")
}
$argsList = @('bundletool.py','prepare','--export',$expectedExport,'--bundle',$BundlePath)
if ($StrictSnapshot) { $argsList += @('--expect-chat-records',"$ExpectChatRecords",'--expect-message-records',"$ExpectMessageRecords") }
& .\.venv\Scripts\python.exe @argsList
if ($LASTEXITCODE -ne 0) { throw (T "Импорт не закончен. НЕ отправляй этот каталог на VPS: $BundlePath" "The import did not finish. Do NOT upload this folder to a VPS: $BundlePath") }
& .\.venv\Scripts\python.exe bundletool.py verify --bundle $BundlePath --full
if ($LASTEXITCODE -ne 0) { throw (T 'Проверка не пройдена. НЕ отправляй архив на VPS.' 'Verification failed. Do NOT upload the archive to a VPS.') }
Write-Host ("`n" + (T "ГОТОВО: $BundlePath" "DONE: $BundlePath")) -ForegroundColor Green
