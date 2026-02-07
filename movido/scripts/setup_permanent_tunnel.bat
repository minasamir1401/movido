@echo off
TITLE Cloudflared Named Tunnel Setup (URL ثابت)
COLOR 0E

echo ====================================
echo   CLOUDFLARED NAMED TUNNEL SETUP
echo   (URL ثابت - لا يتغير)
echo ====================================
echo.

:: Check if cloudflared exists
if not exist "backend\bin\cloudflared.exe" (
    echo [ERROR] cloudflared.exe not found!
    pause
    exit /b 1
)

echo هذا السكريبت سيساعدك في إنشاء Tunnel دائم بـ URL ثابت
echo.
echo المتطلبات:
echo   1. حساب Cloudflare (مجاني)
echo   2. Domain name (اختياري)
echo.
echo الخطوات:
echo   1. تسجيل الدخول لـ Cloudflare
echo   2. إنشاء Named Tunnel
echo   3. الحصول على URL ثابت
echo.
pause

echo.
echo [STEP 1/4] تسجيل الدخول لـ Cloudflare...
echo سيفتح المتصفح للتسجيل...
echo.

backend\bin\cloudflared.exe tunnel login

if %errorlevel% neq 0 (
    echo [ERROR] فشل تسجيل الدخول
    pause
    exit /b 1
)

echo.
echo [SUCCESS] تم تسجيل الدخول بنجاح!
echo.

:: Ask for tunnel name
set /p TUNNEL_NAME="أدخل اسم الـ Tunnel (مثال: movido-backend): "
if "%TUNNEL_NAME%"=="" set TUNNEL_NAME=movido-backend

echo.
echo [STEP 2/4] إنشاء Tunnel باسم: %TUNNEL_NAME%
backend\bin\cloudflared.exe tunnel create %TUNNEL_NAME%

if %errorlevel% neq 0 (
    echo [WARNING] Tunnel موجود بالفعل أو حدث خطأ
    echo سنحاول استخدام الـ tunnel الموجود...
)

echo.
echo [STEP 3/4] الحصول على معلومات الـ Tunnel...
backend\bin\cloudflared.exe tunnel info %TUNNEL_NAME%

:: Create config file
echo.
echo [STEP 4/4] إنشاء ملف التكوين...

set CONFIG_FILE=backend\cloudflared-config.yml

echo url: http://localhost:8000 > %CONFIG_FILE%
echo tunnel: %TUNNEL_NAME% >> %CONFIG_FILE%
echo credentials-file: %USERPROFILE%\.cloudflared\%TUNNEL_NAME%.json >> %CONFIG_FILE%

echo [SUCCESS] تم إنشاء ملف التكوين: %CONFIG_FILE%
echo.

:: Get tunnel URL
echo ====================================
echo   معلومات الـ Tunnel
echo ====================================
echo.
echo اسم الـ Tunnel: %TUNNEL_NAME%
echo ملف التكوين: %CONFIG_FILE%
echo.

:: Create start script
echo.
echo [BONUS] إنشاء سكريبت تشغيل الـ Named Tunnel...

set START_SCRIPT=start_named_tunnel.bat

echo @echo off > %START_SCRIPT%
echo TITLE %TUNNEL_NAME% - Cloudflared Named Tunnel >> %START_SCRIPT%
echo echo Starting %TUNNEL_NAME% tunnel... >> %START_SCRIPT%
echo backend\bin\cloudflared.exe tunnel run --config backend\cloudflared-config.yml %TUNNEL_NAME% >> %START_SCRIPT%

echo [SUCCESS] تم إنشاء: %START_SCRIPT%
echo.

:: Provide route instructions
echo ====================================
echo   الخطوات التالية
echo ====================================
echo.
echo 1. لإنشاء URL ثابت، قم بتشغيل:
echo    cloudflared tunnel route dns %TUNNEL_NAME% movido.yourdomain.com
echo.
echo    (استبدل yourdomain.com بالـ domain الخاص بك)
echo.
echo 2. إذا لم يكن لديك domain، سيتم استخدام:
echo    https://%TUNNEL_NAME%.trycloudflare.com
echo.
echo 3. لتشغيل الـ Tunnel، استخدم:
echo    start_named_tunnel.bat
echo.
echo 4. الـ URL هذا سيبقى ثابتاً دائماً!
echo.
echo ====================================

pause

:: Ask if user wants to start now
echo.
set /p START_NOW="هل تريد تشغيل الـ Tunnel الآن؟ (y/n): "
if /i "%START_NOW%"=="y" (
    echo.
    echo Starting tunnel...
    start "MOVIDO Named Tunnel" cmd /c "%START_SCRIPT%"
    echo.
    echo Tunnel شغال في نافذة منفصلة
)

echo.
echo تم الانتهاء!
pause
