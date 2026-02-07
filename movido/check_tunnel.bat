@echo off
echo ====================================
echo   CLOUDFLARED TUNNEL STATUS
echo ====================================
echo.

:: Check if cloudflared is running
tasklist /FI "IMAGENAME eq cloudflared.exe" 2>NUL | find /I /N "cloudflared.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [STATUS] Cloudflared is RUNNING
    echo.
) else (
    echo [STATUS] Cloudflared is NOT RUNNING
    echo [HINT] Run controller.bat to start the system
    echo.
    pause
    exit /b
)

:: Check tunnel log
if exist "backend\logs\tunnel.log" (
    echo [TUNNEL URL] Searching for active tunnel...
    echo.
    
    :: Extract URL from log
    for /f "tokens=*" %%a in ('findstr /i "trycloudflare.com" backend\logs\tunnel.log') do (
        echo %%a
    )
    
    echo.
    echo ====================================
    echo.
    
    :: Also check sync log
    if exist "backend\logs\sync.log" (
        echo [SYNC STATUS] Checking .env update status...
        type backend\logs\sync.log
    )
) else (
    echo [ERROR] Tunnel log not found
    echo [HINT] Make sure controller.bat is running
)

echo.
echo ====================================
pause
