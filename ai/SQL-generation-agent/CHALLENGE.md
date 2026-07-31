# چالش جذب کارآموز: طراحی Agent تولید SQL

## توضیح مسئله

در این چالش باید یک agent پایتونی بسازید که پرسش کاربر را به زبان طبیعی دریافت کند و با توجه به schema داده‌شده، یک کوئری SQL مناسب تولید کند.

پروژه روی چند دامنه mock و عمومی تمرین می‌شود:

- داده‌های حسابداری ساختگی با جدول `dbo.MockAccDocLines`
- داده‌های تماس سازمانی ساختگی با جدول `dbo.MockCallLogs`
- داده‌های فروشگاهی ساختگی با جدول‌هایی مثل `dbo.MockOrders` و `dbo.MockProducts`
- داده‌های دانشگاهی ساختگی با جدول‌هایی مثل `dbo.MockStudents` و `dbo.MockEnrollments`

تمام داده‌های داخل `input_data/` ساختگی هستند و فقط برای توسعه و تست محلی قرار داده شده‌اند.

## هدف چالش

تابع شما باید بتواند:

- schema و قوانین دامنه را از ورودی بخواند.
- با استفاده از مدل زبانی معرفی‌شده در `env` کوئری SQL بسازد.
- خروجی مدل را پاک‌سازی کند.
- SQL ناامن، چند statement، یا خارج از schema را رد کند.
- برای گزارش‌های تجمیعی و تفکیکی، ستون‌های لازم را برگرداند.

## کاری که باید انجام دهید

فایل زیر را تکمیل کنید:

```text
starter_code/sql_agent.py
```

تابع الزامی:

```python
def generate_sql(question: str, schema: dict, env: dict) -> str:
    ...
```

نمونه import مورد انتظار:

```python
from sql_agent import generate_sql
```

## ورودی

### `question`

پرسش کاربر به زبان طبیعی، مثلاً:

```python
question = "تعداد اسناد حسابداری به تفکیک سال؟"
```

### `schema`

ساختار دیتابیس و قوانین دامنه، مثل فایل‌های زیر:

```text
input_data/accounting_schema.json
input_data/call_center_schema.json
input_data/store_schema.json
input_data/university_schema.json
```

نمونه:

```python
schema = {
    "database": "MockFinanceDB",
    "dbms_type": "MS SQL SERVER",
    "tables": {
        "dbo.MockAccDocLines": ["FinancialYear", "DocNo", "RialCost", "Kol"]
    }
}
```

### `env`

تنظیمات اجرایی و اطلاعات اتصال به مدل زبانی:

```python
env = {
    "LLM_BASE_URL": "http://localhost:8000/v1",
    "LLM_API_KEY": "provided-by-runtime",
    "LLM_MODEL": "local-model",
    "SQL_DIALECT": "SQLServer",
    "CURRENT_DATE": "2026-06-15",
    "TIMEZONE": "Asia/Tehran",
}
```

هیچ API key واقعی داخل پروژه قرار ندهید.

## خروجی

خروجی تابع باید فقط یک رشته SQL باشد؛ بدون markdown، توضیح، کامنت یا متن اضافه.

نمونه خروجی درست:

```sql
SELECT FinancialYear, COUNT(DISTINCT DocNo) AS document_count
FROM dbo.MockAccDocLines
GROUP BY FinancialYear
ORDER BY FinancialYear;
```

نمونه خروجی نادرست:

```text
برای پاسخ به سؤال، کوئری زیر را اجرا کنید:
SELECT FinancialYear, COUNT(*) FROM dbo.MockAccDocLines GROUP BY FinancialYear;
```

## قرارداد SQL

- خروجی باید فقط یک statement باشد.
- فقط کوئری‌های خواندنی مجاز هستند: `SELECT` و `WITH`.
- دستورهای تغییردهنده یا مخرب مجاز نیستند؛ مانند `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE`.
- کوئری فقط باید از tableها و columnهایی استفاده کند که در `schema` آمده‌اند.
- برای سؤال‌های تفکیکی، برگرداندن چند ستون مرتبط مثل سال/ماه و مقدار تجمیعی مجاز است.
- اگر مدل زبانی خروجی markdown یا متن اضافه تولید کرد، باید آن را پاک‌سازی کنید.
- اگر خروجی مدل ناامن، چند statement یا خارج از schema بود، باید خطای مناسب مانند `ValueError` بدهید.

## نمونه‌ها

### حسابداری

ورودی:

```python
question = "کل درآمد سال مالی ۱۴۰۳ چقدر است؟"
```

خروجی قابل قبول:

```sql
SELECT SUM(ABS(RialCost)) AS total_revenue
FROM dbo.MockAccDocLines
WHERE FinancialYear = '1403' AND Kol LIKE '6%';
```

### تماس‌ها

ورودی:

```python
question = "درصد پاسخ‌گویی در زمان استاندارد"
```

خروجی قابل قبول:

```sql
SELECT InboundRoute,
       SUM(CASE WHEN CallStatus = 'ANSWERED' THEN 1 ELSE 0 END) AS answered_calls
FROM dbo.MockCallLogs
WHERE CallType = 'incoming'
GROUP BY InboundRoute;
```

### فروشگاه

ورودی:

```python
question = "فروش پرداخت‌شده هر شهر چقدر است؟"
```

خروجی قابل قبول:

```sql
SELECT c.City, SUM(o.TotalAmount) AS paid_sales
FROM dbo.MockOrders o
JOIN dbo.MockCustomers c ON c.CustomerId = o.CustomerId
WHERE o.Status = 'paid'
GROUP BY c.City;
```

### دانشگاه

ورودی:

```python
question = "میانگین نمره هر درس در نیمسال 1403-1 چقدر است؟"
```

خروجی قابل قبول:

```sql
SELECT c.CourseTitle, AVG(e.Grade) AS average_grade
FROM dbo.MockEnrollments e
JOIN dbo.MockCourses c ON c.CourseId = e.CourseId
WHERE e.Semester = '1403-1'
GROUP BY c.CourseTitle;
```

## محدودیت‌ها

- نسخه پایتون: `3.11`
- خروجی باید SQL خام باشد.
- استفاده از secret واقعی ممنوع است.
- تست‌های عمومی برای کمک به توسعه هستند و همه حالت‌های ارزیابی نهایی را پوشش نمی‌دهند.

## معیار موفقیت

راه‌حل بهتر معمولاً این ویژگی‌ها را دارد:

- از `env` برای اتصال به مدل OpenAI-compatible استفاده می‌کند.
- خروجی مدل را پاک‌سازی و validate می‌کند.
- جدول/ستون ناشناخته را رد می‌کند.
- SQL مخرب یا چند statement را رد می‌کند.

## اجرای پروژه

ابتدا وابستگی‌ها را نصب کنید:

```bash
pip install -r requirements.txt
```

سپس تست‌های عمومی را اجرا کنید:

```bash
python public_tests/run_all.py
```
