# راهنمای اجرای پروژه SQL Agent

این پکیج یک پروژه کامل برای چالش طراحی agent تولید SQL است. شرکت‌کننده باید کد اولیه داخل `starter_code/` را تکمیل کند و قبل از ارسال، تست‌های عمومی را اجرا کند.

## نصب وابستگی‌ها

از Python 3.11 استفاده کنید:

```bash
python -m venv .venv
```

در ویندوز:

```bash
.venv\Scripts\activate
pip install -r requirements.txt
```

در Linux/macOS:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## نقطه شروع

فایل اصلی برای تکمیل:

```text
starter_code/sql_agent.py
```

تابع الزامی:

```python
def generate_sql(question: str, schema: dict, env: dict) -> str:
    ...
```

## داده‌های نمونه

پوشه `input_data/` شامل schema و داده mock کاملاً ساختگی است. این داده‌ها محرمانه نیستند و فقط برای توسعه و تست محلی استفاده می‌شوند.

دامنه‌های نمونه:

- حسابداری ساختگی
- تماس سازمانی ساختگی
- فروشگاه آنلاین ساختگی
- دانشگاه ساختگی

## نمونه‌ها

پوشه `examples/` یک نمونه ورودی و خروجی برای درک قرارداد تابع دارد.

## اجرای تست‌های عمومی

از ریشه پروژه اجرا کنید:

```bash
python public_tests/run_all.py
```

خروجی تست‌ها در ترمینال نمایش داده می‌شود و فایل `public_test_results.json` هم ساخته می‌شود.

## ارسال نهایی

پس از تکمیل پروژه، همین ساختار را ZIP کنید و ارسال کنید. هیچ secret، API key واقعی، خروجی تست یا فایل غیرضروری را داخل ZIP نهایی خود قرار ندهید.
