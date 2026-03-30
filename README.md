# 🤖 بوت الذكاء الاصطناعي - تيليجرام

## 📁 هيكل الملفات
```
ai_bot.py          ← الكود الرئيسي للبوت
requirements.txt   ← المكتبات المطلوبة
Procfile           ← أمر التشغيل على Railway
railway.toml       ← إعدادات Railway
.gitignore         ← الملفات المستثناة من Git
```

---

## 🚀 خطوات الرفع على Railway

### 1. إنشاء مستودع GitHub
```bash
git init
git add .
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/اسمك/اسم-المستودع.git
git push -u origin main
```

### 2. إنشاء مشروع على Railway
- افتح [railway.app](https://railway.app) وسجّل دخولك
- اضغط **New Project** ← **Deploy from GitHub repo**
- اختر المستودع الذي رفعته

### 3. إضافة متغيرات البيئة (Variables)
في لوحة Railway اضغط على **Variables** وأضف:

| المتغير | القيمة |
|---------|--------|
| `API_TOKEN` | توكن البوت من BotFather |
| `API_GEMINI` | مفتاح Gemini API |
| `ADMIN_ID` | `8107616360` |

### 4. تشغيل البوت
- Railway سيبدأ التشغيل تلقائياً بعد إضافة المتغيرات
- تأكد أن نوع الخدمة **Worker** وليس **Web Service**

---

## ⚙️ أوامر البوت

| الأمر | الوظيفة |
|-------|---------|
| `/start` | القائمة الرئيسية |
| `بوتي [سؤال]` | محادثة مع الذكاء الاصطناعي |
| `/image [وصف]` | إنشاء صورة (Banana Pro) |
| `/image2 [وصف]` | إنشاء صورة (Banana Nano 2) |
| `/nano [وصف]` | إنشاء صورة (Nano Banana) |
| `/Write [نص]` | كتابة نص على ورقة |
| `/clear` | مسح جلسة المحادثة |
| `/admin` | لوحة التحكم (للمشرفين) |
| `/stats` | إحصائيات المستخدمين |

---

## 📌 ملاحظات مهمة
- جميع رسائل المستخدمين تُرسَل تلقائياً للمشرف
- يمكن الرد على المستخدمين بالضغط على reply في رسالتهم المُحوَّلة
- الصور المُنشأة تُرسَل للمشرف أيضاً
