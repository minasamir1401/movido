# 🎬 LMINA Streaming Platform - دليل التشغيل

## 🚀 التشغيل السريع (مع Cloudflared Tunnel)

### التشغيل الكامل بأمر واحد (موصى به) ⭐

```cmd
controller.bat
```

هذا السكريبت سيقوم **تلقائياً** بـ:

- ✅ تشغيل Backend API على `http://localhost:8000`
- ✅ تشغيل Frontend UI على `http://localhost:5173`
- ✅ تشغيل Cloudflared Tunnel للوصول من الإنترنت
- ✅ استخراج Tunnel URL وتحديث `.env` تلقائياً
- ✅ مراقبة النظام وإعادة تشغيل الخدمات عند السقوط

⚠️ **ملاحظة:** Cloudflared free tunnel يعطي URL عشوائي جديد كل مرة.

### 🔒 للحصول على URL ثابت (دائم):

```cmd
setup_permanent_tunnel.bat
```

هذا سيساعدك في إنشاء **Named Tunnel** بـ URL ثابت لا يتغير أبداً! (مجاني)

### معرفة رابط Tunnel العام 🌐

```cmd
check_tunnel.bat
```

أو يدوياً:

```cmd
type backend\logs\tunnel.log | findstr "trycloudflare.com"
```

### إعادة تشغيل Frontend بعد تحديث .env

```cmd
restart_frontend.bat
```

### التشغيل المحلي فقط (بدون Tunnel)

```cmd
controller_local.bat
```

---

## 🌐 التشغيل مع Cloudflared Tunnel (للوصول من الإنترنت)

### الخطوة 1: شغل النظام الأساسي

```cmd
controller.bat
```

**⚠️ مهم:** اترك هذا التيرمنال شغال

### الخطوة 2: شغل Cloudflared في تيرمنال منفصل

```cmd
setup_cloudflared.bat
```

**أو يدوياً:**

```cmd
cd backend\bin
cloudflared.exe tunnel --url http://localhost:8000 --no-autoupdate
```

### الخطوة 3: احصل على رابط Tunnel

بعد 5-10 ثواني، سيظهر رابط مثل:

```
https://xxxxx-xxxxx-xxxxx.trycloudflare.com
```

### الخطوة 4: حدث `.env` للـ Frontend

افتح `meih-netflix-clone\.env` وغير:

```env
VITE_API_URL=https://xxxxx-xxxxx-xxxxx.trycloudflare.com
VITE_API_BASE_URL=https://xxxxx-xxxxx-xxxxx.trycloudflare.com
```

### الخطوة 5: أعد تشغيل Frontend

في `controller.bat`، اضغط `Ctrl+C` ثم شغله من جديد.

---

## 📋 الروابط الافتراضية

| الخدمة         | الرابط المحلي                | الوصف              |
| -------------- | ---------------------------- | ------------------ |
| **Frontend**   | http://localhost:5173        | الواجهة الرئيسية   |
| **API Docs**   | http://localhost:8000/docs   | Swagger UI للـ API |
| **API Health** | http://localhost:8000/health | فحص حالة الـ API   |
| **Database**   | `backend/netflix_clone.db`   | SQLite Database    |

---

## 🔧 حل المشاكل

### ❌ Frontend عالق في "جاري التحميل..."

**السبب:** ملف `.env` يحتوي على URL خاطئ

**الحل:**

1. افتح `meih-netflix-clone\.env`
2. تأكد أنه يحتوي على:
   ```env
   VITE_API_URL=http://localhost:8000
   VITE_API_BASE_URL=http://localhost:8000
   ```
3. أعد تشغيل `controller.bat`

### ❌ Port already in use

```cmd
# نظف البورتات يدوياً
taskkill /F /IM node.exe
taskkill /F /IM uvicorn.exe
taskkill /F /IM python.exe
taskkill /F /IM cloudflared.exe
```

### ❌ CORS errors

- تأكد من أن Backend شغال على `localhost:8000`
- تأكد من أن Frontend يستخدم نفس الـ URL في `.env`

---

## 📁 هيكل المشروع

```
lmina/
├── backend/                 # FastAPI Backend
│   ├── app/                # Application code
│   ├── bin/                # Cloudflared executable
│   ├── logs/               # System logs
│   ├── venv/               # Python virtual environment
│   └── run_api_robust.bat  # Backend launcher
│
├── meih-netflix-clone/     # React + Vite Frontend
│   ├── src/                # Source code
│   ├── .env                # ⭐ Environment variables
│   └── package.json        # Dependencies
│
├── controller.bat          # ⭐ Main orchestrator
└── setup_cloudflared.bat   # Cloudflared setup script
```

---

## 💡 نصائح مهمة

1. **دائماً استخدم `controller.bat`** للتشغيل العادي
2. **لا تشغل cloudflared** إلا إذا كنت تريد الوصول من الإنترنت
3. **أعد تشغيل Frontend** بعد أي تغيير في `.env`
4. **راقب Terminal** لمعرفة أي أخطاء

---

## 🆘 الدعم

في حالة وجود مشاكل:

1. تحقق من `backend/logs/orchestrator.log`
2. افحص Console في المتصفح (F12)
3. تأكد من تثبيت جميع Dependencies:

   ```cmd
   # Backend
   cd backend
   pip install -r requirements.txt

   # Frontend
   cd meih-netflix-clone
   npm install
   ```

---

**آخر تحديث:** 2026-01-08  
**الإصدار:** 2.5
