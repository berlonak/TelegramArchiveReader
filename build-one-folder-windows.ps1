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
Set-Location $PSScriptRoot
if ($StrictSnapshot -and ($ExpectChatRecords -le 0 -or $ExpectMessageRecords -le 0)) {
  throw '-StrictSnapshot требует -ExpectChatRecords и -ExpectMessageRecords (числа из отчёта экспорта).'
}
if (-not $ExportPath) { $ExportPath = Read-Host 'Путь к папке экспорта Telegram (result.json)' }
$ExportPath = $ExportPath.Trim('"').Trim("'")
$export = (Resolve-Path -LiteralPath $ExportPath -ErrorAction Stop).Path.TrimEnd('\')
if (-not (Test-Path -LiteralPath (Join-Path $export 'result.json') -PathType Leaf)) {
  throw "Файл result.json не найден: $export"
}
if (-not $BundlePath) { $BundlePath = Join-Path (Split-Path $export -Parent) 'TelegramArchive-ready' }
$BundlePath = [IO.Path]::GetFullPath($BundlePath).TrimEnd('\')
$expectedExport = Join-Path (Join-Path $BundlePath 'exports') 'first-export'
if ([IO.Path]::GetPathRoot($export).ToLowerInvariant() -ne [IO.Path]::GetPathRoot($BundlePath).ToLowerInvariant() -and -not $CopyExport) {
  throw 'Режим переноса работает только на одном диске. Для другого диска запусти с -CopyExport.'
}
# Exclude source/destination self-nesting, including cases with trailing slashes.
$e = $export.ToLowerInvariant() + '\'
$b = $BundlePath.ToLowerInvariant() + '\'
if ($e.StartsWith($b) -or $b.StartsWith($e)) {
  throw 'Экспорт и папка готового архива не должны лежать друг внутри друга.'
}
# An old failed v0.3.1 build may have left only ready/exports (empty).
# Never delete, move or overwrite unknown data in a previous ready directory.
if (Test-Path -LiteralPath $BundlePath) {
  if (Test-Path -LiteralPath (Join-Path $BundlePath 'bundle-manifest.json')) {
    throw "Готовый пакет уже существует: $BundlePath. Не запускай импорт второй раз. Для смены пароля есть RESET-PASSWORD.bat."
  }
  $allowed = @('exports', 'data')
  $unexpected = @(Get-ChildItem -LiteralPath $BundlePath -Force | Where-Object { $allowed -notcontains $_.Name })
  if ($unexpected.Count -gt 0) {
    throw "В $BundlePath лежат файлы незавершённой сборки. Не удаляй их автоматически; проверь содержимое или укажи ДРУГОЙ BundlePath."
  }
  $exportsRoot = Join-Path $BundlePath 'exports'
  if (Test-Path -LiteralPath $exportsRoot) {
    $exportContents = @(Get-ChildItem -LiteralPath $exportsRoot -Force)
    if ($exportContents.Count -gt 0) {
      throw "В $exportsRoot уже есть данные. После неудачного переноса файлы могли разделиться между папками. Остановись и проверь обе папки вручную."
    }
  }
  $dataRoot = Join-Path $BundlePath 'data'
  if (Test-Path -LiteralPath $dataRoot) {
    $dataContents = @(Get-ChildItem -LiteralPath $dataRoot -Force | Where-Object {
      $_.Name -notin @('archive.sqlite3', 'archive.sqlite3-wal', 'archive.sqlite3-shm')
    })
    if ($dataContents.Count -gt 0) {
      throw "Неожиданные файлы в $dataRoot. Проверь папку перед повторным запуском."
    }
  }
}
Write-Host "`nЭкспорт: $export" -ForegroundColor Cyan
Write-Host "Готовый пакет: $BundlePath"
if ($CopyExport) {
  Write-Host 'Выбран режим КОПИРОВАНИЯ. Понадобится дополнительно столько же свободного места, сколько занимает экспорт.' -ForegroundColor Yellow
  $confirmation = Read-Host 'Для подтверждения введи КОПИРОВАТЬ'
  if ($confirmation -cne 'КОПИРОВАТЬ') { throw 'Отменено: исходные данные не затронуты.' }
} else {
  Write-Host "Экспорт будет ПЕРЕМЕЩЁН в $expectedExport (не удалён)." -ForegroundColor Yellow
  Write-Host 'Закрой Telegram Archive, Python, проводники и редакторы, открывшие экспорт.' -ForegroundColor Yellow
  $confirmation = Read-Host 'Для подтверждения введи ПЕРЕМЕСТИТЬ'
  if ($confirmation -cne 'ПЕРЕМЕСТИТЬ') { throw 'Отменено: исходные данные не затронуты.' }
}
# Dependencies and password are checked before moving the source directory.
py -3 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Нужен Python 3.10+; экспорт не перенесён.' }
& .\.venv\Scripts\python.exe -m pip install -e .
if ($LASTEXITCODE -ne 0) { throw 'Не удалось установить библиотеки; экспорт не перенесён.' }
New-Item -ItemType Directory -Path (Join-Path $BundlePath 'exports') -Force | Out-Null
& .\.venv\Scripts\python.exe bundletool.py preflight-password --bundle $BundlePath --gui
if ($LASTEXITCODE -ne 0) { throw 'Пароль не подтверждён. Экспорт остался на месте.' }
if (Test-Path -LiteralPath $expectedExport) {
  throw "Папка назначения уже существует: $expectedExport. Не перезаписывай старую сборку."
}
try {
  if ($CopyExport) {
    Copy-Item -LiteralPath $export -Destination $expectedExport -Recurse -ErrorAction Stop
  } else {
    Move-Item -LiteralPath $export -Destination $expectedExport -ErrorAction Stop
  }
} catch {
  Write-Host "`nОШИБКА: Windows не смогла перенести/скопировать папку." -ForegroundColor Red
  Write-Host 'Закрой START-LOCAL, Python, VS Code, окна Проводника и программы, которые могли открыть экспорт.' -ForegroundColor Yellow
  Write-Host "Проверь обе папки: $export  и  $expectedExport"
  Write-Host 'Ничего не удаляй, если файлы оказались в обеих папках.' -ForegroundColor Yellow
  Write-Host "Причина Windows: $_" -ForegroundColor Red
  Write-Host "`nЗапускаю диагностику открытых файлов и каталогов..." -ForegroundColor Yellow
  try {
    & (Join-Path $PSScriptRoot 'CHECK-LOCK-WINDOWS.ps1') -ExportPath $export
  } catch {
    Write-Host "Диагностика недоступна: $_" -ForegroundColor Yellow
    Write-Host 'Можно отдельно запустить CHECK-LOCK.bat от администратора.' -ForegroundColor Yellow
  }
  throw 'Перемещение не выполнено. Проверь обе папки перед повтором: перенос мог остановиться частично.'
}
if (-not (Test-Path -LiteralPath (Join-Path $expectedExport 'result.json'))) {
  throw "После переноса result.json отсутствует: $expectedExport. НЕ удаляй исходник."
}
$argsList = @('bundletool.py','prepare','--export',$expectedExport,'--bundle',$BundlePath)
if ($StrictSnapshot) { $argsList += @('--expect-chat-records',"$ExpectChatRecords",'--expect-message-records',"$ExpectMessageRecords") }
& .\.venv\Scripts\python.exe @argsList
if ($LASTEXITCODE -ne 0) { throw "Импорт не закончен. НЕ отправляй этот каталог на VPS: $BundlePath" }
& .\.venv\Scripts\python.exe bundletool.py verify --bundle $BundlePath --full
if ($LASTEXITCODE -ne 0) { throw 'Проверка не пройдена. НЕ отправляй архив на VPS.' }
Write-Host "`nГОТОВО: $BundlePath" -ForegroundColor Green
