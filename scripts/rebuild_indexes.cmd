@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0rebuild_indexes.ps1"
exit /b %ERRORLEVEL%
