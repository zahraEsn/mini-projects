# RAG Agent — راهنمای اجرا

## ساختار پروژه

```
├── CHALLENGE.md          # توضیح کامل سؤال
├── README.md             # این فایل
├── .env.example          # نمونه متغیرهای محیطی
├── requirements.txt      # کتابخانه‌های موردنیاز
├── starter_code/
│   └── solution.py       # فایلی که باید تکمیل کنید
├── input_data/
│   └── documents.json    # اسناد نمونه برای تست محلی
├── examples/
│   ├── example_input.json
│   └── example_output.json
└── public_tests/
    ├── README.md
    ├── run_all.py
    └── test_*.py
```

## راه‌اندازی

```bash
pip install -r requirements.txt
```

فایل `.env.example` را کپی کنید و مقادیر LLM را پر کنید:

```bash
cp .env.example .env
# مقادیر LLM_BASE_URL، LLM_API_KEY، LLM_MODEL_NAME را از اطلاعات داده‌شده وارد کنید
```

## تکمیل پروژه

فایل `starter_code/solution.py` را باز کنید و تابع `rag_agent` را پیاده‌سازی کنید.

## اجرای تست‌های عمومی

```bash
python public_tests/run_all.py
```

## ارسال پروژه

فایل `solution.py` تکمیل‌شده را آپلود کنید.
