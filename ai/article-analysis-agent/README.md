# شروع کار

این پوشه شامل:

```
candidate_package/
├── CHALLENGE.md           ← شرح کامل چالش — اول این را بخوان
├── agent.py               ← نقطه شروع — کلاس Agent را اینجا تکمیل کن
├── pdf_to_markdown.py     ← آماده، استفاده کن (تغییر نده)
├── rhino_provider.py      ← آماده، استفاده کن (تغییر نده)
├── requirements.txt       ← وابستگی‌های لازم برای اجرای ابزارهای آماده
├── .env.example           ← نمونه — مقادیر واقعی را جداگانه دریافت می‌کنی
├── input_pdfs/            ← مقالات PDF برای تست
└── public_tests/          ← تست‌های خودارزیابی — قبل از ارسال اجرا کن
```

## اجرای تست‌های عمومی

قبل از ارسال نهایی، تحویل‌دادنی‌هایت را طبق ساختار توضیح‌داده‌شده در `CHALLENGE.md` در یک پوشه `submission/` کنار `public_tests/` بگذار و اجرا کن:

```bash
cd public_tests
python run_all.py --submission_dir ./submission --input_pdfs ../input_pdfs
```

جزئیات بیشتر در `public_tests/README.md`.

## نصب سریع

```bash
pip install -r requirements.txt
```

(بقیه وابستگی‌هایی که خودت لازم داری را هم به همین `requirements.txt` اضافه کن)

## تنظیم .env

```bash
cp .env.example .env
# سپس RHINO_CHAT_URL و RHINO_API_KEY واقعی را در .env قرار بده
```

## شروع

```python
from pdf_to_markdown import convert_folder

articles = convert_folder("input_pdfs/")
print(f"{len(articles)} مقاله بارگذاری شد")
```

برای ادامه، `CHALLENGE.md` را بخوان.

موفق باشی! 🚀
