@echo off
rem copyright by berlonak
rem telegram: @Kilax123
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONPATH=%~dp0app"
if not exist "bundle-manifest.json" goto no_bundle
if not exist "data\archive.sqlite3" goto no_bundle
set "PYTHON=%~dp0..\.tgarchive-local-venv\Scripts\python.exe"
if not exist "%PYTHON%" goto no_python
echo Stop START-LOCAL.bat before changing the password.
"%PYTHON%" "%~dp0bundletool.py" reset-password --bundle "%~dp0" --gui
if errorlevel 1 goto failure
echo Password changed without reimporting messages or media.
pause
exit /b 0
:no_python
echo Local Python environment not found. Run START-LOCAL.bat once, then stop it.
goto failure
:no_bundle
echo Run this file from inside a completed TelegramArchive-ready folder.
goto failure
:failure
echo.
echo PASSWORD RESET FAILED.
pause
exit /b 1
