@echo off
TITLE Restart Frontend with Updated Tunnel URL
COLOR 0A

echo ====================================
echo   FRONTEND RESTART UTILITY
echo ====================================
echo.

:: Kill existing frontend
echo [1/3] Stopping existing frontend processes...
taskkill /F /IM node.exe /FI "WINDOWTITLE eq LMINA_UI*" >nul 2>&1

:: Wait a moment
timeout /t 2 /nobreak >nul

:: Show current .env
echo [2/3] Current .env configuration:
echo.
if exist "meih-netflix-clone\.env" (
    type "meih-netflix-clone\.env"
) else (
    echo [WARNING] .env file not found!
)

echo.
echo [3/3] Starting frontend with updated configuration...
cd /d "%~dp0meih-netflix-clone"
start /min "LMINA_UI" cmd /c "npm run dev"

echo.
echo ====================================
echo   Frontend restarted successfully!
echo   - Access: http://localhost:5173
echo ====================================
echo.
timeout /t 3
