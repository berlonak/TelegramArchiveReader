@echo off
rem copyright by berlonak
rem telegram: @Kilax123
setlocal
cd /d "%~dp0"
set /p "EXPORT_DIR=Path to Telegram export directory (result.json): "
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0CHECK-LOCK-WINDOWS.ps1" -ExportPath "%EXPORT_DIR%"
echo.
pause
