@echo off
REM install.bat
REM -----------
REM Double-click this file to install ProductLabelPrint.
REM It automatically:
REM   1. Asks Windows for Administrator permission (a UAC prompt will
REM      pop up - click "Yes").
REM   2. Runs install.ps1 with the execution policy bypassed, so you
REM      never see the "running scripts is disabled on this system"
REM      error.
REM
REM Keep this file in the same folder as install.ps1 and the other
REM ProductLabelPrint files.

REM Check whether this window is already running as Administrator.
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting Administrator permission - click "Yes" on the prompt...
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"

echo.
echo Installer finished. Press any key to close this window.
pause >nul
