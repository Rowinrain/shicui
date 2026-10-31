@echo off
rem Create desktop and Start menu shortcuts that open the app in its own window.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0windows-setup.ps1"
pause
