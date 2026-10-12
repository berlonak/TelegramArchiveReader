@echo off
rem copyright by berlonak
rem telegram: @Kilax123
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
set "PYTHONUTF8=1"
title Telegram Archive - Local Windows
rem Messages are Russian or English (TGARCHIVE_LANG, otherwise the Windows display language).
rem Cyrillic text needs a UTF-8 console: switch to code page 65001 and restore the old one on exit.
set "TG_OLDCP="
for /f "tokens=2 delims=:" %%C in ('chcp') do set "TG_OLDCP=%%C"
if defined TG_OLDCP set "TG_OLDCP=%TG_OLDCP: =%"
if defined TG_OLDCP set "TG_OLDCP=%TG_OLDCP:.=%"
chcp 65001 >nul
call :detect_lang

echo =====================================
call :say "    Telegram Archive - локальный запуск" "    Telegram Archive - local start"
echo =====================================
echo.
if not exist "bundle-manifest.json" goto no_bundle
if not exist "data\archive.sqlite3" goto no_database
if not exist "app\pyproject.toml" goto no_app
if not exist "start-local.py" goto no_launcher

rem Keep the Windows venv OUTSIDE the portable bundle.
set "VENV=%~dp0..\.tgarchive-local-venv"
if exist "%VENV%\Scripts\python.exe" goto venv_ready

call :say "Создаю локальное окружение Python..." "Creating local Python environment..."
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

call :say "Устанавливаю зависимости приложения (при первом запуске нужен интернет)..." "Installing application dependencies (first launch needs internet)..."
"%VENV%\Scripts\python.exe" -m pip install -e "%~dp0app"
if errorlevel 1 goto failure

:run_app
echo.
call :say "Запускаю локальный веб-сервер: http://127.0.0.1:8000" "Starting local web server on http://127.0.0.1:8000"
echo.
"%VENV%\Scripts\python.exe" "%~dp0start-local.py"
if errorlevel 1 goto failure

echo.
call :say "Локальный сервер остановлен." "Local server stopped."
pause
call :restore_cp
exit /b 0

:no_bundle
call :say "ОШИБКА: положи ОБА файла запуска в TelegramArchive-ready рядом с bundle-manifest.json." "ERROR: Put BOTH launch files in TelegramArchive-ready next to bundle-manifest.json."
goto failure
:no_database
call :say "ОШИБКА: не найден data\archive.sqlite3; проверь готовый пакет." "ERROR: Cannot find data\archive.sqlite3; check your ready bundle."
goto failure
:no_app
call :say "ОШИБКА: не найден app\pyproject.toml; проверь готовый пакет." "ERROR: Cannot find app\pyproject.toml; check your ready bundle."
goto failure
:no_launcher
call :say "ОШИБКА: в этой папке нет start-local.py." "ERROR: Cannot find start-local.py in this folder."
goto failure
:no_python
call :say "ОШИБКА: нужен Python 3.10+. Установи его и повтори." "ERROR: Python 3.10+ is required. Install it and retry."
goto failure
:old_python
call :say "ОШИБКА: Python в .tgarchive-local-venv старше 3.10." "ERROR: Python in .tgarchive-local-venv is older than 3.10."
call :say "Переименуй папку .tgarchive-local-venv рядом с TelegramArchive-ready," "Rename the .tgarchive-local-venv folder next to TelegramArchive-ready,"
call :say "затем установи Python 3.10+ и снова запусти этот файл." "then install Python 3.10+ and run this file again."
goto failure
:failure
echo.
call :say "ЗАПУСК НЕ УДАЛСЯ. Скопируй сообщения об ошибке выше, если нужна помощь." "START FAILED. Copy the error messages above if you need help."
pause
call :restore_cp
exit /b 1

:detect_lang
set "TG_LANG="
if /i "%TGARCHIVE_LANG%"=="ru" set "TG_LANG=ru"
if /i "%TGARCHIVE_LANG%"=="en" set "TG_LANG=en"
if defined TG_LANG goto lang_done
set "TG_UI="
for /f %%L in ('powershell.exe -NoProfile -Command "[Globalization.CultureInfo]::CurrentUICulture.TwoLetterISOLanguageName" 2^>nul') do set "TG_UI=%%L"
set "TG_LANG=en"
for %%R in (ru uk be kk) do if /i "%TG_UI%"=="%%R" set "TG_LANG=ru"
:lang_done
set "TGARCHIVE_LANG=%TG_LANG%"
exit /b 0

rem Usage: call :say "Russian text" "English text"  (no quotes, ampersands, pipes, angle brackets, carets or percent signs inside)
:say
if "%TG_LANG%"=="ru" goto say_ru
echo(%~2
exit /b 0
:say_ru
echo(%~1
exit /b 0

:restore_cp
if defined TG_OLDCP chcp %TG_OLDCP% >nul
exit /b 0
