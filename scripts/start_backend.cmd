@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_backend.ps1"
exit /b %ERRORLEVEL%
