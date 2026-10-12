@echo off
rem copyright by berlonak
rem telegram: @Kilax123
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
set "PYTHONUTF8=1"
title Telegram Archive - Local Windows

echo =====================================
echo     Telegram Archive - local start
echo =====================================
echo.
if not exist "bundle-manifest.json" goto no_bundle
if not exist "data\archive.sqlite3" goto no_database
if not exist "app\pyproject.toml" goto no_app
if not exist "start-local.py" goto no_launcher

rem Keep the Windows venv OUTSIDE the portable bundle.
set "VENV=%~dp0..\.tgarchive-local-venv"
if exist "%VENV%\Scripts\python.exe" goto venv_ready

echo Creating local Python environment...
where py >nul 2>nul
if not errorlevel 1 goto use_py
where python >nul 2>nul
if not errorlevel 1 goto use_python
goto no_python

:use_py
py -3 -m venv "%VENV%"
if errorlevel 1 goto failure
goto venv_ready

:use_python
python -m venv "%VENV%"
if errorlevel 1 goto failure

:venv_ready
"%VENV%\Scripts\python.exe" -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 goto old_python

"%VENV%\Scripts\python.exe" -c "import fastapi, uvicorn, argon2, ijson, tgarchive" >nul 2>nul
if not errorlevel 1 goto run_app

echo Installing application dependencies (first launch needs internet)...
"%VENV%\Scripts\python.exe" -m pip install -e "%~dp0app"
if errorlevel 1 goto failure

:run_app
echo.
echo Starting local web server on http://127.0.0.1:8000
echo.
"%VENV%\Scripts\python.exe" "%~dp0start-local.py"
if errorlevel 1 goto failure

echo.
echo Local server stopped.
pause
exit /b 0

:no_bundle
echo ERROR: Put BOTH launch files in TelegramArchive-ready next to bundle-manifest.json.
goto failure
:no_database
echo ERROR: Cannot find data\archive.sqlite3; check your ready bundle.
goto failure
:no_app
echo ERROR: Cannot find app\pyproject.toml; check your ready bundle.
goto failure
:no_launcher
echo ERROR: Cannot find start-local.py in this folder.
goto failure
:no_python
echo ERROR: Python 3.10+ is required. Install it and retry.
goto failure
:old_python
echo ERROR: Python in .tgarchive-local-venv is older than 3.10.
echo Rename the .tgarchive-local-venv folder next to TelegramArchive-ready,
echo then install Python 3.10+ and run this file again.
goto failure
:failure
echo.
echo START FAILED. Copy the error messages above if you need help.
pause
exit /b 1
