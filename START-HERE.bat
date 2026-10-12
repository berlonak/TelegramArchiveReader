@echo off
rem copyright by berlonak
rem telegram: @Kilax123
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
rem All messages (Russian or English) come from the PowerShell builder, so this file stays ASCII.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build-one-folder-windows.ps1"
echo.
pause
