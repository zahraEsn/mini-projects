"""
test_execution_io.py

بررسی می‌کند که:
- برنامه از خط فرمان قابل اجرا است
- ورودی (فولدر PDF) و خروجی (مسیر فایل .md) درست پذیرفته می‌شود
- در زمان معقول اجرا می‌شود
- خروجی واقعاً ساخته می‌شود

اجرا:
    python test_execution_io.py --submission_dir ./submission --input_pdfs ../input_pdfs
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

TIME_LIMIT_SECONDS = 600  # ۵ دقیقه


def find_agent_script(submission_dir: Path) -> Path | None:
    for name in ["agent.py", "main.py", "run.py"]:
        p = submission_dir / name
        if p.exists():
            return p
    candidates = list(submission_dir.glob("*.py"))
    return candidates[0] if candidates else None


def run_tests(submission_dir: Path, input_pdfs: Path) -> list[tuple[str, bool, str]]:
    results = []

    # تست ۱: فایل اصلی اجرا وجود دارد
    script = find_agent_script(submission_dir)
    results.append(
        (
            "فایل اصلی اجرا (agent.py) وجود دارد",
            script is not None,
            str(script) if script else "هیچ فایل .py پیدا نشد",
        )
    )
    if script is None:
        return results

    # تست ۲: requirements.txt وجود دارد
    req = submission_dir / "requirements.txt"
    results.append(
        (
            "requirements.txt وجود دارد",
            req.exists(),
            "" if req.exists() else "فایل پیدا نشد",
        )
    )

    # تست ۳: README.md وجود دارد
    readme = submission_dir / "README.md"
    results.append(
        (
            "README.md وجود دارد",
            readme.exists() and readme.stat().st_size > 100,
            "" if readme.exists() else "فایل پیدا نشد یا خیلی کوچک است",
        )
    )

    # تست ۴: اجرا با --input_folder و --output بدون کرش
    output_path = submission_dir / "_test_output.md"
    if output_path.exists():
        output_path.unlink()

    cmd = [
        sys.executable,
        str(script),
        "--input_folder",
        str(input_pdfs),
        "--output",
        str(output_path),
    ]
    start = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=submission_dir,
            capture_output=True,
            text=True,
            timeout=TIME_LIMIT_SECONDS,
        )
        elapsed = time.time() - start
        success = proc.returncode == 0
        detail = proc.stderr[-400:] if not success else f"{elapsed:.1f} ثانیه"
        results.append(("اجرا بدون خطا با --input_folder و --output", success, detail))
    except subprocess.TimeoutExpired:
        results.append(
            (
                "اجرا بدون خطا با --input_folder و --output",
                False,
                f"بیش از {TIME_LIMIT_SECONDS} ثانیه طول کشید",
            )
        )
        return results
    except Exception as e:
        results.append(("اجرا بدون خطا با --input_folder و --output", False, str(e)))
        return results

    # تست ۵: زمان اجرا منطقی است
    results.append(
        (
            f"زمان اجرا کمتر از {TIME_LIMIT_SECONDS} ثانیه",
            elapsed < TIME_LIMIT_SECONDS,
            f"{elapsed:.1f} ثانیه",
        )
    )

    # تست ۶: فایل خروجی ساخته شده
    output_exists = output_path.exists()
    results.append(
        (
            "فایل خروجی .md ساخته شده است",
            output_exists,
            str(output_path) if output_exists else "فایل پیدا نشد",
        )
    )

    # تست ۷: sample_output/report.md هم وجود دارد (طبق تحویل‌دادنی‌ها)
    sample = submission_dir / "sample_output" / "report.md"
    results.append(
        (
            "sample_output/report.md وجود دارد",
            sample.exists() and sample.stat().st_size > 200,
            "" if sample.exists() else "فایل پیدا نشد یا خیلی کوچک است",
        )
    )

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission_dir", required=True)
    parser.add_argument("--input_pdfs", required=True)
    args = parser.parse_args()

    results = run_tests(Path(args.submission_dir), Path(args.input_pdfs))

    print("\n--- اجرا و ورودی/خروجی ---")
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
