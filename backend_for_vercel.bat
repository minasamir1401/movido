@echo off
TITLE LMINA BACKEND + CLOUDFLARED (For Vercel Deployment)
COLOR 0B

echo ====================================
echo   BACKEND + CLOUDFLARED ONLY
echo   (For Vercel Frontend Deploy)
echo ====================================
echo.

:: Cleanup
echo [1/4] Cleaning up old processes...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM cloudflared.exe >nul 2>&1

timeout /t 2 /nobreak >nul

:: Start Backend
echo [2/4] Starting Backend API...
cd /d "%~dp0backend"
start /min "LMINA_BACKEND" cmd /c "run_api_robust.bat"

timeout /t 5 /nobreak >nul

:: Start Cloudflared
echo [3/4] Starting Cloudflared Tunnel...
cd /d "%~dp0"
if not exist "backend\logs" mkdir "backend\logs"
echo. > backend\logs\tunnel.log

start "CLOUDFLARED_TUNNEL" cmd /c "backend\bin\cloudflared.exe tunnel --url http://localhost:8000 --no-autoupdate"

echo [4/4] Waiting for tunnel URL...
timeout /t 15 /nobreak >nul

echo.
echo ====================================
echo   BACKEND ONLINE - READY FOR VERCEL
echo ====================================
echo.

:: Extract and display tunnel URL
for /f "tokens=*" %%a in ('findstr /i "trycloudflare.com" backend\logs\tunnel.log 2^>nul') do (
    echo %%a
)

echo.
echo Copy the tunnel URL above and use it in Vercel:
echo   VITE_API_URL=https://xxxxx.trycloudflare.com
echo   VITE_API_BASE_URL=https://xxxxx.trycloudflare.com
echo.
echo Press any key to see the tunnel URL again...
pause >nul

:show_url
cls
echo ====================================
echo   CLOUDFLARED TUNNEL URL
echo ====================================
echo.
for /f "tokens=*" %%a in ('findstr /i "https://" backend\logs\tunnel.log 2^>nul ^| findstr "trycloudflare"') do (
    echo %%a
)
echo.
echo ====================================
echo Keep this window open while deploying to Vercel!
echo Press Ctrl+C to stop
echo.
timeout /t 30 >nul
goto show_url
