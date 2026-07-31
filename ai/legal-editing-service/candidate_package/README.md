# راهنمای شروع (Quick Start)

به چالش **سرویس ویراستاری حقوقی با استفاده از مدل‌های زبانی بزرگ (LLM)** خوش آمدید.

شرح کامل مسئله، الزامات، فرمت ورودی و خروجی و معیارهای ارزیابی در فایل **CHALLENGE.md** ارائه شده است.

---

# راه‌اندازی محیط (Setup)

## 1- ایجاد محیط مجازی (اختیاری)

```bash
python -m venv .venv
```

فعال‌سازی محیط:

**Windows**

```bash
.venv\Scripts\activate
```

**Linux / macOS**

```bash
source .venv/bin/activate
```

---

## 2- نصب وابستگی‌ها

```bash
pip install -r requirements.txt
```

---

## 3- تنظیم متغیرهای محیطی

فایل `.env.example` را با نام `.env` کپی کرده و مقادیر زیر را تکمیل کنید.

```text
LLM_API_KEY=YOUR_API_KEY
LLM_BASE_URL=YOUR_BASE_URL
LLM_MODEL=YOUR_MODEL_NAME
```

> **توجه:** در محیط ارزیابی، این متغیرها به صورت خودکار تنظیم خواهند شد و نیازی به قرار دادن مقادیر واقعی در فایل ارسالی نیست.

---

# نحوه اجرای کد

در کد خود (یا در یک اسکریپت جدید داخل `starter_code/`):

```python
from ClarityWritingEvaluator import ClarityWritingEvaluator

decision_text = "..."

evaluator = ClarityWritingEvaluator()

result = evaluator.evaluate(decision_text)

print(result.model_dump())
```

---

# نحوه ارسال (Submission)

پس از تکمیل پیاده‌سازی، فایل‌ها و ساختار پوشه‌ها را بدون تغییر نگه دارید.

ساختار پوشه ارسالی باید به صورت زیر باشد:

```text
candidate_package/

├── README.md
├── .env.example
├── requirements.txt
└── starter_code/
    └── ClarityWritingEvaluator.py   (فایلی که باید تکمیل کنید)
```

می‌توانید در صورت نیاز فایل‌های کمکی دیگری هم داخل `starter_code/` اضافه کنید، اما فایل و کلاس اصلی که سیستم فراخوانی می‌کند همان `ClarityWritingEvaluator.py` است.

سپس پوشه **candidate_package** را مطابق دستورالعمل سامانه در قالب فایل ZIP ارسال کنید.

> **توجه:** فقط فایل‌های موجود در `candidate_package` باید ارسال شوند. از ارسال فایل‌های اضافی یا تغییر ساختار پوشه‌ها خودداری کنید.

---

# اجرای تست‌های عمومی

پیش از ارسال نهایی، تست‌های عمومی موجود در پوشه `public_tests/` را اجرا کنید.

دستور اجرا از مسیر ریشه چالش:

```bash
python public_tests/run_all.py \
  --submission_dir candidate_package/starter_code \
  --output results.json
```

نتیجه اجرای تست‌ها در فایل `results.json` ذخیره می‌شود.

> پوشه `public_tests/` بخشی از بسته ارسالی نیست و فقط برای بررسی صحت پیاده‌سازی قبل از ارسال استفاده می‌شود.

---

# نکات

- شرح کامل چالش در فایل **CHALLENGE.md** قرار دارد.
- اطلاعات محرمانه مانند API Key را در کد یا فایل‌های ارسالی قرار ندهید.
- پیش از ارسال، از اجرای صحیح برنامه روی نمونه موجود اطمینان حاصل کنید.

موفق باشید.
