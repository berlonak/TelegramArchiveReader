# copyright by berlonak
# telegram: @Kilax123
# Resume only if the ORIGINAL EXPORT has already been staged in ready/exports/first-export.
# Refuse to overwrite any partially imported database or completed archive.
param([string]$BundlePath = '')
$ErrorActionPreference = 'Stop'
# Messages follow TGARCHIVE_LANG (ru/en), otherwise the Windows display language.
$TgLang = if (@('ru', 'en') -contains "$env:TGARCHIVE_LANG".ToLowerInvariant()) { "$env:TGARCHIVE_LANG".ToLowerInvariant() }
          elseif (@('ru', 'uk', 'be', 'kk') -contains (Get-UICulture).TwoLetterISOLanguageName) { 'ru' } else { 'en' }
$env:TGARCHIVE_LANG = $TgLang
function T([string]$Ru, [string]$En) { if ($TgLang -eq 'ru') { $Ru } else { $En } }
trap {
  Write-Host ''
  Write-Host (T 'ВОССТАНОВЛЕНИЕ НЕ УДАЛОСЬ (причина ниже). Сохрани ОБЕ папки (исходную и ready); ничего не удаляй.' `
                'RESUME FAILED (reason below). Keep BOTH source and ready folders; do not delete anything.') -ForegroundColor Red
  break
}
Set-Location $PSScriptRoot
if (-not $BundlePath) { $BundlePath = Read-Host (T 'Полный путь к НЕЗАВЕРШЁННОЙ папке TelegramArchive-ready' 'Full path to an INCOMPLETE TelegramArchive-ready folder') }
$BundlePath = [IO.Path]::GetFullPath($BundlePath.Trim('"').Trim("'"))
$export = Join-Path (Join-Path $BundlePath 'exports') 'first-export'
if (Test-Path -LiteralPath (Join-Path $BundlePath 'bundle-manifest.json')) {
  throw (T 'Этот архив уже готов. Используй START-LOCAL.bat или RESET-PASSWORD.bat.' `
           'This archive is already complete. Use START-LOCAL.bat or RESET-PASSWORD.bat instead.')
}
if (-not (Test-Path -LiteralPath (Join-Path $export 'result.json') -PathType Leaf)) {
  throw (T "Перенесённый result.json НЕ найден: $export. Не используй RESUME; проверь исходную и ready папки." `
           "Staged result.json NOT found: $export. Do not use RESUME; inspect source and ready folders.")
}
$original = Read-Host (T 'ПОЛНЫЙ путь к ИСХОДНОЙ папке экспорта ДО переноса (чтобы заметить частичный перенос)' `
                         'FULL path to the ORIGINAL export folder, BEFORE the move (to detect split move)')
if (-not $original) { throw (T 'Нужен путь к исходной папке. Данные не изменены.' 'Original source path is required. No data was modified.') }
$original = [IO.Path]::GetFullPath($original.Trim('"').Trim("'"))
if (Test-Path -LiteralPath $original -PathType Container) {
  $leftovers = @(Get-ChildItem -LiteralPath $original -Force | Select-Object -First 1)
  if ($leftovers.Count -gt 0) {
    throw (T "В ИСХОДНОЙ папке ещё есть файлы: $original. Экспорт мог разделиться при неудачном переносе. Сравни папки перед продолжением; ничего не удаляй." `
             "The ORIGINAL folder still contains files: $original. The export might have been split by a failed move. Compare folders before resuming; do not delete either.")
  }
}
Write-Host (T 'Продолжаю НЕЗАВЕРШЁННУЮ сборку. Исходные медиа не перемещаются и не копируются повторно.' `
              'Resuming an INCOMPLETE staged build. Original media will not be moved or re-copied.') -ForegroundColor Cyan
py -3 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw (T 'Нужен Python 3.10+.' 'Python 3.10+ is required.') }
& .\.venv\Scripts\python.exe -m pip install -e .
if ($LASTEXITCODE -ne 0) { throw (T 'Не удалось установить зависимости.' 'Dependencies installation failed.') }
& .\.venv\Scripts\python.exe bundletool.py preflight-password --bundle $BundlePath --gui
if ($LASTEXITCODE -ne 0) { throw (T 'В базе уже есть импортированные данные или ввод пароля отменён. Ничего не удалено.' `
                                    'Existing DB contains imported data or password dialog was cancelled. Nothing was deleted.') }
& .\.venv\Scripts\python.exe bundletool.py prepare --export $export --bundle $BundlePath
if ($LASTEXITCODE -ne 0) { throw (T 'Сборка не завершена. Сохрани экспорт и базу без изменений для диагностики.' `
                                    'Build not finished. Keep the export and DB intact for diagnosis.') }
& .\.venv\Scripts\python.exe bundletool.py verify --bundle $BundlePath --full
if ($LASTEXITCODE -ne 0) { throw (T 'Проверка не пройдена. Не загружай на сервер.' 'Verification failed. Do not upload to server.') }
Write-Host (T "ГОТОВО: $BundlePath" "DONE: $BundlePath") -ForegroundColor Green
