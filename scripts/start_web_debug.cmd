@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_web_debug.ps1"
exit /b %ERRORLEVEL%
