@echo off
rem copyright by berlonak
rem telegram: @Kilax123
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
rem All messages (Russian or English) come from the PowerShell script, so this file stays ASCII.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0RESUME-READY-WINDOWS.ps1"
echo.
pause
