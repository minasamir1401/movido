@echo off
setlocal enabledelayedexpansion

TITLE MOVIDO ENTERPRISE ORCHESTRATOR v3.0
COLOR 0B

echo.
echo  #####################################################################
echo  #                                                                   #
echo  #    MOVIDO STREAMING PLATFORM - ENTERPRISE ORCHESTRATOR             #
echo  #    STATUS: BOOTING SYSTEM COMPONENTS...                           #
echo  #                                                                   #
echo  #####################################################################
echo.

:: --- 1. SESSION INITIALIZATION ---
echo [SYSTEM] Starting MOVIDO services...
timeout /t 1 >nul

:: --- 2. ENVIRONMENT CLEANUP ---
echo [SYSTEM] Cleaning legacy process environment...
taskkill /F /IM node.exe /T >nul 2>&1
taskkill /F /IM uvicorn.exe /T >nul 2>&1
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM cloudflared.exe /T >nul 2>&1

echo [SYSTEM] Reclaiming network ports (8000, 5173)...
for %%p in (8000 5173) do (
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr :%%p ^| findstr LISTENING') do (
        echo    - Force closing PID %%a on port %%p
        taskkill /F /PID %%a >nul 2>&1
    )
)

:: --- 3. DEPENDENCY VALIDATION ---
echo [SYSTEM] Validating runtime dependencies...
where python >nul 2>&1 || (echo [ERROR] Python missing! && pause && exit /b)
where npm >nul 2>&1 || (echo [ERROR] Node.js missing! && pause && exit /b)

:: --- 4. PRE-FLIGHT SETUP ---
if not exist "backend\logs" mkdir "backend\logs"
set "LOG_FILE=backend\logs\orchestrator.log"
echo [%date% %time%] SYSTEM BOOT START > "%LOG_FILE%"

:: --- 5. SYSTEM LAUNCH SEQUENCE ---
echo [SYSTEM] Initializing Microservices...

:: A. Backend API Implementation
echo    - Launching API Gateway Matrix...
cd /d "%~dp0backend"
start /min "MOVIDO_API" cmd /c "run_api_robust.bat"

:: Wait for backend to initialize
echo [SYSTEM] Waiting for backend initialization...
timeout /t 5 /nobreak >nul

:: B. Cloudflared Tunnel (Start BEFORE Frontend)
cd /d "%~dp0"
if exist "backend\bin\cloudflared.exe" (
    echo    - Establishing Secure Network Tunnel...
    if not exist "backend\logs" mkdir "backend\logs"
    
    :: Clear old logs
    echo. > backend\logs\tunnel.log
    echo. > backend\logs\sync.log
    
    :: Start cloudflared
    start /min "MOVIDO_TUNNEL" cmd /c "backend\bin\cloudflared.exe tunnel --url http://localhost:8000 --no-autoupdate > backend\logs\tunnel.log 2>&1"
    
    :: Wait for tunnel to establish
    echo    - Waiting for tunnel URL...
    timeout /t 8 /nobreak >nul
    
    :: Extract and update .env synchronously
    echo    - Extracting Tunnel URL...
    cd /d "%~dp0backend"
    "%~dp0backend\venv\Scripts\python.exe" update_tunnel_url.py > "%~dp0backend\logs\sync.log" 2>&1
    
    :: Show tunnel URL
    echo.
    echo    ╔══════════════════════════════════════════════════════════════╗
    for /f "tokens=*" %%a in ('findstr /i "trycloudflare.com" "%~dp0backend\logs\tunnel.log" 2^>nul') do (
        echo    ║  %%a
    )
    echo    ╚══════════════════════════════════════════════════════════════╝
    echo.
    
    cd /d "%~dp0"
) else (
    echo    [WARNING] Cloudflared not found, skipping tunnel setup
)

:: C. Frontend Engine (Start AFTER updating .env)
echo    - Igniting Frontend UI Engine...
cd /d "%~dp0meih-netflix-clone"

:: Display current .env
echo    - Current Frontend Configuration:
if exist ".env" (
    for /f "tokens=*" %%a in (.env) do echo      %%a
)

start /min "MOVIDO_UI" cmd /c "npm run dev"

:: Small delay to let frontend start
timeout /t 3 /nobreak >nul

cd /d "%~dp0"

echo.
echo  =====================================================================
echo    SYSTEM ONLINE - CLOUDFLARED TUNNEL ENABLED
echo  =====================================================================
echo.
echo  Local Access:
echo    - API Docs:   http://localhost:8000/docs
echo    - Frontend:   http://localhost:5173
echo.
echo  Public Access (Cloudflare Tunnel):
for /f "tokens=*" %%a in ('findstr /i "https://" backend\logs\tunnel.log 2^>nul ^| findstr "trycloudflare"') do (
    echo    - Tunnel URL: %%a
)
echo.
echo  Tip: Run 'check_tunnel.bat' anytime to see the tunnel URL
echo.
echo  [WATCHDOG] Monitoring system health... (Press Ctrl+C to stop)
echo.

:: --- 6. ENTERPRISE WATCHDOG LOOP ---
:watchdog
timeout /t 15 /nobreak >nul

:: Check API (Port 8000)
netstat -aon | findstr :8000 | findstr LISTENING >nul
if %errorlevel% neq 0 (
    echo [%time%] [ALERT] API Gateway Offline! Restarting...
    cd /d "%~dp0backend"
    start /min "MOVIDO_API" cmd /c "run_api_robust.bat"
    echo [%time%] [RECOVERY] API Gateway auto-restored. >> "%~dp0%LOG_FILE%"
)

:: Check Frontend (Port 5173)
netstat -aon | findstr :5173 | findstr LISTENING >nul
if %errorlevel% neq 0 (
    echo [%time%] [ALERT] Frontend UI Offline! Restarting...
    cd /d "%~dp0meih-netflix-clone"
    start /min "MOVIDO_UI" cmd /c "npm run dev"
    echo [%time%] [RECOVERY] Frontend UI auto-restored. >> "%~dp0%LOG_FILE%"
)

:: Check Cloudflared
tasklist /FI "IMAGENAME eq cloudflared.exe" 2>NUL | find /I /N "cloudflared.exe">NUL
if "%ERRORLEVEL%" neq "0" (
    echo [%time%] [ALERT] Cloudflared Tunnel Offline! Restarting...
    start /min "MOVIDO_TUNNEL" cmd /c "backend\bin\cloudflared.exe tunnel --url http://localhost:8000 --no-autoupdate > backend\logs\tunnel.log 2>&1"
    echo [%time%] [RECOVERY] Cloudflared Tunnel auto-restored. >> "%~dp0%LOG_FILE%"
)

goto watchdog
