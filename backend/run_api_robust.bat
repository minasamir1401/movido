@echo off
setlocal enabledelayedexpansion
TITLE LMINA BACKEND API (AUTO-RESTART)
cd /d "%~dp0"

:loop
echo.
echo [INFO] Starting LMINA API Server...
echo [INFO] Time: %time%
echo.

call venv\Scripts\uvicorn app.main:app --port 8000 --host 0.0.0.0 --log-level info

echo.
echo [WARNING] API Server crashed or stopped!
echo [WARNING] Restarting in 2 seconds...
echo.
timeout /t 2 /nobreak >nul
goto loop
