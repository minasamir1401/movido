@echo off
setlocal enabledelayedexpansion

TITLE MOVIDO LOCAL MODE - No Tunnel
COLOR 0A

echo.
echo  #####################################################################
echo  #                                                                   #
echo  #    MOVIDO STREAMING PLATFORM - LOCAL MODE                          #
echo  #    (No Cloudflared Tunnel - Localhost Only)                       #
echo  #                                                                   #
echo  #####################################################################
echo.

:: Cleanup
echo [SYSTEM] Cleaning up old processes...
taskkill /F /IM node.exe /T >nul 2>&1
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM cloudflared.exe /T >nul 2>&1

:: Set .env to localhost
echo [SYSTEM] Configuring for localhost...
echo VITE_API_URL=http://localhost:8000 > meih-netflix-clone\.env
echo VITE_API_BASE_URL=http://localhost:8000 >> meih-netflix-clone\.env

:: Start Backend
echo [SYSTEM] Starting Backend...
cd /d "%~dp0backend"
start /min "MOVIDO_API" cmd /c "run_api_robust.bat"

timeout /t 5 /nobreak >nul

:: Start Frontend
echo [SYSTEM] Starting Frontend...
cd /d "%~dp0meih-netflix-clone"
start /min "MOVIDO_UI" cmd /c "npm run dev"

timeout /t 3 /nobreak >nul

echo.
echo  =====================================================================
echo    SYSTEM ONLINE - LOCAL MODE
echo  =====================================================================
echo.
echo  Access URLs:
echo    - API Docs:   http://localhost:8000/docs
echo    - Frontend:   http://localhost:5173
echo.
echo  Note: This mode is localhost only. No public access.
echo  To enable public access, use: controller.bat
echo.
pause
