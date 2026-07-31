"""
test_overall_quality.py

بررسی می‌کند که محتوای گزارش از نظر سبک کلی قابل قبول است:
- زبان فارسی غالب است
- حجم کافی دارد
- placeholder یا متن ناقص باقی نمانده
- ادعای نمودار وجود دارد (حداقل دو مورد طبق طرح سوال)
- نشانه‌هایی از زبان تحلیلی دیده می‌شود (نه فقط کپی/خلاصه)

⚠️ این تست‌ها دقت محتوا را بررسی نمی‌کنند (آن کار LLM Judge است) —
   فقط بررسی می‌کنند که گزارش از نظر ظاهری و حجمی قابل قبول است.

اجرا:
    python test_overall_quality.py --report ./submission/sample_output/report.md
"""

import argparse
import re
from pathlib import Path

MIN_WORD_COUNT = 600

PLACEHOLDER_PATTERNS = [
    "lorem ipsum", "todo", "fixme", "placeholder",
    "اینجا بنویسید", "متن نمونه", "xxx", "tbd",
]

ANALYTICAL_KEYWORDS = [
    "بنابراین", "از این رو", "در نتیجه", "مقایسه", "افزایش", "کاهش",
    "روند", "نشان می‌دهد", "حاکی از", "تأثیر", "تحلیل", "ارتباط",
    "therefore", "indicates", "trend", "compared",
]

CHART_REFERENCE_PATTERNS = [
    r'!\[.*?\]\(.*?\)',          # ![...](...) تصویر مارک‌داون
    r'نمودار\s*\d',               # "نمودار ۱"، "نمودار 2"
    r'شکل\s*\d',                  # "شکل ۱"
    r'```mermaid',                 # نمودار mermaid
    r'```chart',
]


def word_count(text: str) -> int:
    return len(text.split())


def persian_ratio(text: str) -> float:
    fa = len(re.findall(r'[\u0600-\u06FF]', text))
    en = len(re.findall(r'[a-zA-Z]', text))
    total = fa + en
    return fa / total if total else 0.0


def find_placeholders(text: str) -> list[str]:
    low = text.lower()
    return [p for p in PLACEHOLDER_PATTERNS if p in low]


def count_analytical_keywords(text: str) -> int:
    return sum(1 for k in ANALYTICAL_KEYWORDS if k in text)


def count_chart_references(text: str) -> int:
    count = 0
    for pattern in CHART_REFERENCE_PATTERNS:
        count += len(re.findall(pattern, text, re.IGNORECASE))
    return count


def run_tests(report_path: Path) -> list[tuple[str, bool, str]]:
    results = []

    if not report_path.exists():
        results.append(("فایل گزارش وجود دارد", False, str(report_path)))
        return results

    text = report_path.read_text(encoding="utf-8")

    # حجم کافی
    wc = word_count(text)
    results.append((
        f"حداقل {MIN_WORD_COUNT} کلمه",
        wc >= MIN_WORD_COUNT,
        f"{wc} کلمه"
    ))

    # زبان فارسی غالب
    ratio = persian_ratio(text)
    results.append((
        "زبان فارسی غالب (بیش از ۴۰٪)",
        ratio > 0.4,
        f"{ratio:.0%} فارسی"
    ))

    # بدون placeholder
    placeholders = find_placeholders(text)
    results.append((
        "بدون متن placeholder یا ناقص",
        len(placeholders) == 0,
        f"یافت شد: {placeholders}" if placeholders else ""
    ))

    # حداقل دو ارجاع به نمودار (طبق طرح سوال)
    n_charts = count_chart_references(text)
    results.append((
        "حداقل دو ارجاع به نمودار/شکل در متن",
        n_charts >= 2,
        f"{n_charts} ارجاع پیدا شد"
    ))

    # نشانه‌هایی از زبان تحلیلی
    n_analytical = count_analytical_keywords(text)
    results.append((
        "نشانه‌هایی از زبان تحلیلی (نه فقط خلاصه)",
        n_analytical >= 3,
        f"{n_analytical} کلمه تحلیلی پیدا شد"
    ))

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    results = run_tests(Path(args.report))

    print("\n--- کیفیت کلی محتوا ---")
    passed = 0
    for name, ok, detail in results:
        icon = "✅" if ok else "❌"
        print(f"{icon} {name}")
        if detail:
            print(f"    {detail}")
        if ok:
            passed += 1

    print(f"\nنتیجه: {passed} از {len(results)}")
    return passed, len(results)


if __name__ == "__main__":
    main()
