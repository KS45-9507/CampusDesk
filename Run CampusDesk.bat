@echo off
setlocal
cd /d "%~dp0"
title CampusDesk One-Click Launcher

where powershell.exe >nul 2>nul
if errorlevel 1 (
    echo Windows PowerShell was not found.
    pause
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_campusdesk.ps1"
if errorlevel 1 (
    echo.
    echo CampusDesk did not start. Read the message above and check web_server_stderr.log.
    pause
)
endlocal
