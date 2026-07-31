#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path


def run_test(test_file: Path, project_root: Path, max_score: int) -> dict:
    started = time.perf_counter()
    env = os.environ.copy()
    submission_dir = project_root / "starter_code"
    env["SUBMISSION_DIR"] = str(submission_dir.resolve())
    env["PYTHONPATH"] = os.pathsep.join(
        [str(submission_dir.resolve()), env.get("PYTHONPATH", "")]
    )

    completed = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file), "-q"],
        cwd=str(test_file.parent),
        env=env,
        text=True,
        capture_output=True,
        timeout=120,
    )
    duration_ms = int((time.perf_counter() - started) * 1000)
    passed = completed.returncode == 0
    output = (completed.stdout + "\n" + completed.stderr).strip()

    return {
        "name": test_file.stem,
        "passed": passed,
        "score": max_score if passed else 0,
        "max_score": max_score,
        "message": "passed" if passed else output[-1000:],
        "duration_ms": duration_ms,
    }


def main() -> int:
    print("Running public tests...")
    project_root = Path(__file__).resolve().parents[1]
    output_path = project_root / "public_test_results.json"
    test_files = sorted(Path(__file__).parent.glob("test_*.py"))
    per_test_score = 30 // max(1, len(test_files))
    remainder = 30 - per_test_score * len(test_files)

    results = {
        "tests": [],
        "total_score": 0,
        "max_score": 30,
        "status": "pending",
    }

    for index, test_file in enumerate(test_files):
        max_score = per_test_score + (1 if index < remainder else 0)
        test_result = run_test(test_file, project_root, max_score)
        results["tests"].append(test_result)
        results["total_score"] += test_result["score"]
        marker = "✓" if test_result["passed"] else "✗"
        print(f"{marker} {test_result['name']}")

    if results["total_score"] == results["max_score"]:
        results["status"] = "passed"
    elif results["total_score"] > 0:
        results["status"] = "partial"
    else:
        results["status"] = "failed"

    print(f"{sum(1 for item in results['tests'] if item['passed'])}/{len(results['tests'])} Passed")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    return 0 if results["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
