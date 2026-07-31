#!/usr/bin/env python3
"""
Run all public tests for Q1 — RAG Agent.

Usage:
    python public_tests/run_all.py
"""
import re
import subprocess
import sys
from pathlib import Path


def prettify(name):
    # test_basic_scenario -> Basic scenario
    name = name.replace("test_", "").replace("_", " ")
    return name.capitalize()


def main():
    test_dir = Path(__file__).parent
    extra_args = sys.argv[1:]

    print("Running public tests...\n")

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "pytest",
            str(test_dir),
            "-v",
            "--no-header",
            "--tb=short",
            "-k",
            "not test_citations or test_citations",
        ] + extra_args,
        cwd=str(test_dir.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    passed = failed = 0

    for line in process.stdout:
        line = line.strip()

        m = re.search(r"::(test_[^\s]+)\s+(PASSED|FAILED)", line)
        if m:
            test_name = prettify(m.group(1))
            status = m.group(2)

            if status == "PASSED":
                passed += 1
                print(f"✓ {test_name}")
            else:
                failed += 1
                print(f"✗ {test_name}")

    process.wait()

    total = passed + failed

    if failed == 0:
        print(f"\n{passed}/{total} Passed")
    else:
        print(f"\n{passed}/{total} Passed ({failed} Failed)")

    sys.exit(process.returncode)


if __name__ == "__main__":
    main()