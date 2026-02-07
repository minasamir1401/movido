@echo off
setlocal enabledelayedexpansion
TITLE MOVIDO BACKEND API (AUTO-RESTART)
cd /d "%~dp0"

:loop
echo.
echo [INFO] Starting MOVIDO API Server...
echo [INFO] Time: %time%
echo.

call venv\Scripts\uvicorn app.main:app --reload --port 8000 --host 0.0.0.0 --log-level info --workers 4 --loop asyncio --timeout-keep-alive 65

echo.
echo [WARNING] API Server crashed or stopped!
echo [WARNING] Restarting in 2 seconds...
echo.
timeout /t 2 /nobreak >nul
goto loop
