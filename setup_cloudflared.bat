@echo off
echo ====================================
echo   CLOUDFLARED TUNNEL SETUP
echo ====================================
echo.

:: Kill old cloudflared
echo [1/4] Stopping old cloudflared instances...
taskkill /F /IM cloudflared.exe >nul 2>&1

:: Wait a moment
timeout /t 2 /nobreak >nul

:: Start cloudflared in background and capture output
echo [2/4] Starting new cloudflared tunnel...
cd /d "%~dp0backend\bin"
start /min "CLOUDFLARED_TUNNEL" cmd /c "cloudflared.exe tunnel --url http://localhost:8000 --no-autoupdate > ..\logs\tunnel.log 2>&1"

:: Wait for tunnel to establish
echo [3/4] Waiting for tunnel to establish...
timeout /t 10 /nobreak >nul

:: Extract and update ENV
echo [4/4] Updating frontend configuration...
cd /d "%~dp0backend"
python update_tunnel_url.py

echo.
echo ====================================
echo   TUNNEL SETUP COMPLETE!
echo ====================================
echo.
echo Check backend\logs\tunnel.log for the tunnel URL
echo.
pause
