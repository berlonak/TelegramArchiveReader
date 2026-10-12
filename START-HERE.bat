@echo off
rem copyright by berlonak
rem telegram: @Kilax123
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build-one-folder-windows.ps1"
if errorlevel 1 (
  echo.
  echo BUILD FAILED. Read the error messages above.
)
echo.
pause
