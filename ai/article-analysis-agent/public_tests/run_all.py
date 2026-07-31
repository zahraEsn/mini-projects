"""
run_all.py — اجرای همه تست‌های فولدر «تست» و جمع‌بندی نتیجه

این فایل خودش هر فایل .py داخل پوشه «تست» را پیدا می‌کند و اجرا می‌کند —
اگر فایل تست جدیدی به این پوشه اضافه شود، خودکار وارد محاسبه می‌شود.

قرارداد: هر فایل تست باید تابع run_tests(submission_dir, input_pdfs=None) یا
run_tests(report_path) داشته باشد — این فایل بر اساس نام پارامترهای واقعی
تابع (نه نام فایل) تشخیص می‌دهد چه چیزی را پاس بدهد.

اجرا:
    python run_all.py --submission_dir ./submission --input_pdfs ../input_pdfs
"""

import argparse
import importlib.util
import inspect
from pathlib import Path

TEST_DIR = Path(__file__).parent


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def discover_test_files() -> list[Path]:
    files = sorted(TEST_DIR.glob("*.py"))
    return [f for f in files if f.name != "run_all.py"]


def call_run_tests(module, submission_dir: Path, input_pdfs: Path, report_path: Path):
    """بر اساس نام پارامترهای واقعی run_tests تشخیص می‌دهد چه آرگومانی پاس بدهد."""
    sig = inspect.signature(module.run_tests)
    params = list(sig.parameters.keys())

    kwargs = {}
    for p in params:
        if p == "submission_dir":
            kwargs[p] = submission_dir
        elif p == "input_pdfs":
            kwargs[p] = input_pdfs
        elif p == "report_path" or p == "report":
            kwargs[p] = report_path

    return module.run_tests(**kwargs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission_dir", required=True)
    parser.add_argument("--input_pdfs", required=True)
    args = parser.parse_args()

    submission_dir = Path(args.submission_dir)
    input_pdfs = Path(args.input_pdfs)
    report_path = submission_dir / "sample_output" / "report.md"

    test_files = discover_test_files()
    print(f"📋 {len(test_files)} فایل تست پیدا شد در پوشه «تست»:")
    for f in test_files:
        print(f"   - {f.name}")

    total_passed = 0
    total_tests = 0

    for test_file in test_files:
        module = load_module(test_file)
        results = call_run_tests(module, submission_dir, input_pdfs, report_path)

        print(f"\n{'='*55}")
        print(f"  {test_file.stem}")
        print(f"{'='*55}")

        passed = 0
        for name, ok, detail in results:
            icon = "✅" if ok else "❌"
            print(f"  {icon} {name}")
            if detail:
                print(f"      {detail}")
            if ok:
                passed += 1

        print(f"  → {passed} از {len(results)}")
        total_passed += passed
        total_tests += len(results)

    print(f"\n{'='*55}")
    print(f"  📊 نتیجه کلی تست‌های اولیه: {total_passed} از {total_tests}")
    print(f"{'='*55}")
    print(f"\n  ⏳ ارزیابی عمیق (دقت محتوا، تحلیل، شکاف‌های پژوهشی)")
    print(f"     طی ۴ روز آینده انجام و اعلام می‌شود.\n")

    return total_passed, total_tests


if __name__ == "__main__":
    main()

