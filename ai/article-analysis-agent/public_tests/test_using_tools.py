"""
test_using_tools.py

بررسی می‌کند که:
- کاندیدا از pdf_to_markdown.py ما استفاده کرده (نه استخراج‌گر دیگری نوشته)
- کاندیدا از rhino_provider.py ما استفاده کرده (نه SDK مدل دیگری)
- کلاس Agent با متد run وجود دارد

⚠️ این تست‌ها فقط روی سطح کد (static) هستند، نه روی نتیجه واقعی اجرا.

اجرا:
    python test_using_tools.py --submission_dir ./submission
"""

import argparse
import re
from pathlib import Path

FORBIDDEN_SDK_PATTERNS = [
    r'\bopenai\b',
    r'\bfrom\s+anthropic\b',
    r'\bimport\s+anthropic\b',
    r'\bgenai\b',          # google generativeai
    r'\bcohere\b',
]

# اگر کاندیدا خودش استخراج PDF نوشته (نشانه‌های معمول)، یعنی به‌جای pdf_to_markdown ما، چیز دیگری نوشته
OWN_PDF_EXTRACTION_HINTS = [
    "pdfplumber", "PdfReader", "pypdf", "PyPDF2", "pdf2image", "pytesseract",
]


def find_main_script(submission_dir: Path) -> Path | None:
    for name in ["agent.py", "main.py", "run.py"]:
        p = submission_dir / name
        if p.exists():
            return p
    candidates = [
        f for f in submission_dir.glob("*.py")
        if f.name not in ("pdf_to_markdown.py", "rhino_provider.py")
    ]
    return candidates[0] if candidates else None


def run_tests(submission_dir: Path, input_pdfs: Path | None = None) -> list[tuple[str, bool, str]]:
    results = []

    script = find_main_script(submission_dir)
    if script is None:
        results.append(("فایل اصلی اجرا پیدا شد", False, "هیچ فایل .py پیدا نشد"))
        return results

    source = script.read_text(encoding="utf-8")

    # تست ۱: pdf_to_markdown.py دست‌نخورده باقی مانده
    pdf_module = submission_dir / "pdf_to_markdown.py"
    pdf_unchanged = pdf_module.exists() and "convert_folder" in pdf_module.read_text(encoding="utf-8")
    results.append((
        "pdf_to_markdown.py دست‌نخورده در submission موجود است",
        pdf_unchanged,
        "" if pdf_unchanged else "فایل پیدا نشد یا تغییر کرده است"
    ))

    # تست ۲: استفاده از convert_folder در کد اصلی
    uses_convert_folder = "convert_folder" in source or "pdf_to_markdown" in source
    results.append((
        "استفاده از pdf_to_markdown.convert_folder در agent.py",
        uses_convert_folder,
        "" if uses_convert_folder else "هیچ ارجاعی به convert_folder/pdf_to_markdown پیدا نشد"
    ))

    # تست ۳: عدم نوشتن استخراج‌گر PDF جدید
    own_extraction_found = [h for h in OWN_PDF_EXTRACTION_HINTS if h in source]
    results.append((
        "عدم نوشتن استخراج‌گر PDF جایگزین",
        len(own_extraction_found) == 0,
        f"یافت شد: {own_extraction_found}" if own_extraction_found else ""
    ))

    # تست ۴: استفاده از rhino_provider
    uses_rhino = "rhino_provider" in source or "RhinoProvider" in source
    results.append((
        "استفاده از rhino_provider.py",
        uses_rhino,
        "" if uses_rhino else "هیچ ارجاعی به RhinoProvider پیدا نشد"
    ))

    # تست ۵: عدم استفاده از SDK های دیگر LLM (در کد و در requirements.txt)
    forbidden_found = []
    for pattern in FORBIDDEN_SDK_PATTERNS:
        if re.search(pattern, source, re.IGNORECASE):
            forbidden_found.append(pattern)

    req_file = submission_dir / "requirements.txt"
    if req_file.exists():
        req_text = req_file.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_SDK_PATTERNS:
            if re.search(pattern, req_text, re.IGNORECASE) and pattern not in forbidden_found:
                forbidden_found.append(f"{pattern} (در requirements.txt)")

    results.append((
        "عدم استفاده از SDK مدل‌های دیگر (OpenAI/Anthropic/...)",
        len(forbidden_found) == 0,
        f"یافت شد: {forbidden_found}" if forbidden_found else ""
    ))

    # تست ۶: کلاس Agent با متد run وجود دارد
    has_agent_class = bool(re.search(r'class\s+Agent\b', source))
    results.append(("کلاس Agent در کد تعریف شده", has_agent_class, ""))

    has_run_method = bool(re.search(r'(async\s+)?def\s+run\s*\(', source))
    results.append(("متد run تعریف شده", has_run_method, ""))

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission_dir", required=True)
    parser.add_argument("--input_pdfs", required=False, default=None)
    args = parser.parse_args()

    results = run_tests(Path(args.submission_dir))

    print("\n--- استفاده از ابزارهای آماده ---")
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
