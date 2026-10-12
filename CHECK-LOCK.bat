@echo off
rem copyright by berlonak
rem telegram: @Kilax123
setlocal
cd /d "%~dp0"
rem The PowerShell script asks for the export folder itself (Unicode-safe input, Russian or English).
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0CHECK-LOCK-WINDOWS.ps1"
echo.
pause
