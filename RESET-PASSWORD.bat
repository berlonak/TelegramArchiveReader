@echo off
rem copyright by berlonak
rem telegram: @Kilax123
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONPATH=%~dp0app"
rem Messages are Russian or English (TGARCHIVE_LANG, otherwise the Windows display language).
rem Cyrillic text needs a UTF-8 console: switch to code page 65001 and restore the old one on exit.
set "TG_OLDCP="
for /f "tokens=2 delims=:" %%C in ('chcp') do set "TG_OLDCP=%%C"
if defined TG_OLDCP set "TG_OLDCP=%TG_OLDCP: =%"
if defined TG_OLDCP set "TG_OLDCP=%TG_OLDCP:.=%"
chcp 65001 >nul
call :detect_lang
if not exist "bundle-manifest.json" goto no_bundle
if not exist "data\archive.sqlite3" goto no_bundle
set "PYTHON=%~dp0..\.tgarchive-local-venv\Scripts\python.exe"
if not exist "%PYTHON%" goto no_python
"%PYTHON%" "%~dp0bundletool.py" reset-password --bundle "%~dp0" --gui
if errorlevel 1 goto failure
pause
call :restore_cp
exit /b 0
:no_python
call :say "Локальное окружение Python не найдено. Один раз запусти START-LOCAL.bat, затем останови его." "Local Python environment not found. Run START-LOCAL.bat once, then stop it."
goto failure
:no_bundle
call :say "Запусти этот файл из готовой папки TelegramArchive-ready." "Run this file from inside a completed TelegramArchive-ready folder."
goto failure
:failure
echo.
call :say "СМЕНА ПАРОЛЯ НЕ УДАЛАСЬ." "PASSWORD RESET FAILED."
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
