@echo off
REM Yetkin360 local launcher. All logic lives in scripts\baslat.ps1:
REM one window, prefixed logs (api / worker / web), cached installs,
REM healthcheck waits. Keys: [B] browser  [H] summary  [Q] / Ctrl+C stop.
REM Options: baslat.bat -NoBrowser
REM This file must keep CRLF line endings (see .gitattributes).
setlocal
chcp 65001 >nul
title Yetkin360
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\baslat.ps1" %*
if errorlevel 1 (
    echo.
    pause
)
endlocal
