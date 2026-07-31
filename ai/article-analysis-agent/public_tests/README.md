# تست‌های عمومی (Public Tests)

این تست‌ها برای بررسی *اولیه* کار شما هستند — قبل از ارسال نهایی اجرایشان کن تا از خطاهای واضح (ساختار، خروجی، استفاده از ابزارهای آماده) مطمئن شوی.

⚠️ این تست‌ها **دقت محتوای گزارش** (تحلیل، شکاف‌های پژوهشی و ...) را بررسی نمی‌کنند — آن ارزیابی جداگانه و بعد از ارسال انجام می‌شود.

## پیش‌نیاز

تحویل‌دادنی‌های خودت را طبق ساختار زیر آماده کن (کنار همین `public_tests/`):

```
submission/
├── agent.py
├── requirements.txt
├── README.md
└── sample_output/
    └── report.md
```

## اجرای همه تست‌ها

```bash
python run_all.py --submission_dir ./submission --input_pdfs ../input_pdfs
```

## اجرای تک‌تک تست‌ها

```bash
python test_execution_io.py --submission_dir ./submission --input_pdfs ../input_pdfs
python test_report_structure.py --report ./submission/sample_output/report.md
python test_overall_quality.py --report ./submission/sample_output/report.md
python test_using_tools.py --submission_dir ./submission
```

## تفسیر خروجی

هر تست به‌صورت ✅ (قبول) یا ❌ (رد) گزارش می‌شود و در پایان جمع «X از Y» نشان داده می‌شود. رد شدن یک مورد یعنی همان بخش را قبل از ارسال اصلاح کن.
