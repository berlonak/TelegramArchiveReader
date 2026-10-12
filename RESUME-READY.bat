@echo off
rem copyright by berlonak
rem telegram: @Kilax123
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0RESUME-READY-WINDOWS.ps1"
if errorlevel 1 (
 echo.
 echo RESUME FAILED. Keep BOTH source and ready folders; do not delete anything.
)
pause
