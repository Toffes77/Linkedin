@echo off
setlocal

set "PROJECT_ROOT=%~dp0"

start "LinkedIn - Backend" cmd.exe /k "cd /d ""%PROJECT_ROOT%backend"" && python -m src.main"
start "LinkedIn - Frontend" cmd.exe /k "cd /d ""%PROJECT_ROOT%frontend"" && npm.cmd run dev"

endlocal
