# 🚀 Deploy LMINA Frontend to Vercel

## 📋 المتطلبات:

1. ✅ حساب على [Vercel](https://vercel.com)
2. ✅ Git repository للـ Frontend (GitHub, GitLab, أو Bitbucket)
3. ✅ Backend شغال مع Cloudflared على جهازك المحلي

---

## 🎯 الخطوات التفصيلية:

### 1️⃣ تحضير Backend (على جهازك المحلي):

```cmd
# شغل Backend + Cloudflared فقط
backend_for_vercel.bat
```

**⏳ انتظر 15-30 ثانية** حتى يظهر Cloudflared URL مثل:

```
https://abc-xyz-123.trycloudflare.com
```

**📝 انسخ هذا الرابط** - ستحتاجه في Vercel!

---

### 2️⃣ تحضير Frontend للرفع:

#### أ. تأكد من `.gitignore`:

تأكد أن ملف `meih-netflix-clone/.gitignore` يحتوي على:

```
.env
.env.local
node_modules/
dist/
```

#### ب. لا ترفع `.env` إلى Git!

الملف `.env` يحتوي على إعدادات محلية فقط. ستضيف المتغيرات في Vercel Dashboard.

---

### 3️⃣ رفع الكود إلى GitHub:

إذا لم يكن لديك repository:

```bash
cd meih-netflix-clone

# Initialize git
git init

# Add all files (excluding .env because of .gitignore)
git add .

# Commit
git commit -m "Initial commit for Vercel deployment"

# Create repository on GitHub and push
git remote add origin https://github.com/YOUR_USERNAME/lmina-frontend.git
git branch -M main
git push -u origin main
```

---

### 4️⃣ Deploy على Vercel:

#### أ. إنشاء مشروع جديد:

1. اذهب إلى [Vercel Dashboard](https://vercel.com/new)
2. اختر "Import Git Repository"
3. اختر الـ repository الخاص بـ `meih-netflix-clone`
4. اضغط "Import"

#### ب. ضبط الإعدادات:

**Framework Preset:** Vite
**Root Directory:** `./` (أو اتركها فارغة)
**Build Command:** `npm run build`
**Output Directory:** `dist`

#### ج. إضافة Environment Variables:

في قسم "Environment Variables"، أضف:

| Key                 | Value                                   |
| ------------------- | --------------------------------------- |
| `VITE_API_URL`      | `https://abc-xyz-123.trycloudflare.com` |
| `VITE_API_BASE_URL` | `https://abc-xyz-123.trycloudflare.com` |

⚠️ **استبدل** `https://abc-xyz-123.trycloudflare.com` **بالرابط الذي حصلت عليه من `backend_for_vercel.bat`**

#### د. Deploy:

اضغط "Deploy" وانتظر حتى ينتهي البناء (1-3 دقائق).

---

### 5️⃣ بعد الـ Deployment:

سيعطيك Vercel رابط مثل:

```
https://lmina-frontend.vercel.app
```

**🎉 افتح الرابط وتمتع بموقعك!**

---

## ⚠️ ملاحظات مهمة:

### 🔴 Cloudflared URL يتغير عند كل إعادة تشغيل!

كلما أعدت تشغيل `backend_for_vercel.bat`، ستحصل على URL جديد.

**الحلول:**

#### 1. **الحل المؤقت (مجاني):**

- عند كل إعادة تشغيل، احصل على الـ URL الجديد
- اذهب إلى Vercel → Settings → Environment Variables
- حدث `VITE_API_URL` و `VITE_API_BASE_URL`
- اضغط "Redeploy" من Deployments tab

#### 2. **الحل الدائم (موصى به):**

**أ. استخدام Cloudflared Named Tunnel (مجاني):**

```bash
# تسجيل وإنشاء tunnel دائم
cloudflared tunnel login
cloudflared tunnel create lmina-backend
cloudflared tunnel route dns lmina-backend lmina-api.yourdomain.com
```

**ب. استخدام VPS (مدفوع):**

- ارفع Backend على VPS (DigitalOcean, Linode, AWS)
- احصل على domain ثابت
- استخدمه في Vercel بدون قلق

**ج. استخدام Ngrok (بديل لـ Cloudflared):**

```bash
ngrok http 8000
```

---

## 🔄 تحديث الموقع:

كل تغيير تعمله في الكود:

1. `git add .`
2. `git commit -m "Update message"`
3. `git push`
4. Vercel سيعيد البناء تلقائياً! ✨

---

## 🐛 حل المشاكل:

### ❌ "Network Error" في الموقع:

- **السبب:** Backend مش شغال أو Cloudflared URL خطأ
- **الحل:** تأكد من تشغيل `backend_for_vercel.bat` وتحديث Environment Variables

### ❌ "CORS Error":

- **السبب:** Backend لا يسمح بالـ origin الخاص بـ Vercel
- **الحل:** Backend مضبوط بالفعل (`allow_origins=["*"]`)، لكن تأكد من إعادة تشغيله

### ❌ Build Failed على Vercel:

- **السبب:** Dependencies ناقصة أو أخطاء في الكود
- **الحل:**
  ```bash
  # اختبار البناء محلياً قبل الرفع
  cd meih-netflix-clone
  npm run build
  ```

### ❌ "Page not loading" / White Screen:

- **السبب:** مشكلة في الـ routing أو service worker
- **الحل:** تأكد من `vite.config.ts` و `base` path صحيح

---

## 📊 الهيكل النهائي:

```
Frontend (Vercel) ←→ Cloudflared Tunnel ←→ Backend (جهازك المحلي)
    ↓                        ↓                      ↓
https://lmina.vercel.app    https://xyz.trycloudflare.com    http://localhost:8000
```

---

## 🆘 دعم إضافي:

إذا واجهت أي مشاكل، تحقق من:

1. **Vercel Logs:** Dashboard → Deployments → View Logs
2. **Backend Logs:** `backend/logs/`
3. **Browser Console:** F12

---

**آخر تحديث:** 2026-01-08
**الإصدار:** 1.0
