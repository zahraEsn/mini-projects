"""
test_report_structure.py

بررسی می‌کند که گزارش markdown، بخش‌های الزامی طرح سوال را دارد:
- معرفی
- جدول استخراج اطلاعات
- تحلیل روندها
- شکاف‌های پژوهشی
- جمع‌بندی نهایی

این تست‌ها فقط *وجود* بخش را بررسی می‌کنند، نه دقت محتوای آن.

اجرا:
    python test_report_structure.py --report ./submission/sample_output/report.md
"""

import argparse
import re
from pathlib import Path

KEYWORDS = {
    "خلاصه اجرایی": ["خلاصه اجرایی", "خلاصه", "executive summary"],
    "جدول استخراج اطلاعات": ["جدول"],  # جدول مارک‌داون هم جدا چک می‌شود
    "تحلیل روندهای پژوهشی": ["روند", "تحلیل", "trend", "analysis"],
    "شکاف‌های پژوهشی": ["شکاف", "gap"],
    "نتیجه‌گیری": ["نتیجه‌گیری", "نتیجه گیری", "conclusion"],
    "منابع / مستندات پایه": ["منابع", "مستندات", "مراجع", "references", "sources"],
}


def has_markdown_table(text: str) -> bool:
    """تشخیص جدول مارک‌داون: خطی با | و خط جداکننده ---|---"""
    lines = text.splitlines()
    for i, line in enumerate(lines[:-1]):
        if "|" in line and re.match(r'^\s*\|?[\s\-:|]+\|?\s*$', lines[i + 1] or ""):
            return True
    return False


def has_heading(text: str) -> bool:
    return bool(re.search(r'^#{1,3}\s+.{3,}', text, re.MULTILINE))


def count_h2_sections(text: str) -> int:
    return len(re.findall(r'^#{1,3}\s+.+', text, re.MULTILINE))


def has_keywords(text: str, keywords: list[str]) -> bool:
    low = text.lower()
    return any(k.lower() in low for k in keywords)


def has_numbered_or_bulleted_list(text: str) -> bool:
    has_bullets = bool(re.search(r'^[\-\*]\s+.+', text, re.MULTILINE))
    has_numbered = bool(re.search(r'^\d+[\.\)]\s+.+', text, re.MULTILINE))
    return has_bullets or has_numbered


def run_tests(report_path: Path) -> list[tuple[str, bool, str]]:
    results = []

    if not report_path.exists():
        results.append(("فایل گزارش وجود دارد", False, str(report_path)))
        return results

    text = report_path.read_text(encoding="utf-8")
    results.append(("فایل گزارش وجود دارد", True, ""))

    # عنوان اصلی
    results.append((
        "عنوان اصلی گزارش (#) موجود است",
        bool(re.search(r'^#\s+.{5,}', text, re.MULTILINE)),
        ""
    ))

    # بخش‌های الزامی طبق طرح سوال
    for section_name, keywords in KEYWORDS.items():
        ok = has_keywords(text, keywords)
        results.append((f"بخش «{section_name}» وجود دارد", ok, ""))

    # جدول مارک‌داون واقعی
    results.append((
        "جدول مارک‌داون در گزارش موجود است",
        has_markdown_table(text),
        ""
    ))

    # حداقل تعداد بخش‌ها (heading)
    n_sections = count_h2_sections(text)
    results.append((
        "حداقل ۵ بخش (heading) در گزارش وجود دارد",
        n_sections >= 5,
        f"{n_sections} heading پیدا شد"
    ))

    # لیست یا bullet (برای شکاف‌های پژوهشی/یافته‌ها)
    results.append((
        "حداقل یک لیست (bullet/numbered) در گزارش وجود دارد",
        has_numbered_or_bulleted_list(text),
        ""
    ))

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True, help="مسیر فایل report.md")
    args = parser.parse_args()

    results = run_tests(Path(args.report))

    print("\n--- ساختار گزارش ---")
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
