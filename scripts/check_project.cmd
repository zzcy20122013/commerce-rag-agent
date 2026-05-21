@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0check_project.ps1"
exit /b %ERRORLEVEL%
