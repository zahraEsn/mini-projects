#!/usr/bin/env python3
"""
Public Tests Runner
"""

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path


def load_module(file_path):

    spec = importlib.util.spec_from_file_location(
        file_path.stem,
        file_path
    )

    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    return module


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--submission_dir", required=True)

    parser.add_argument("--output", default="results.json")

    args = parser.parse_args()

    results = {
        "tests": [],
        "total_score": 0,
        "max_score": 0,
        "status": "pending",
    }

    test_files = sorted(
        Path(__file__).parent.glob("test_*.py")
    )

    for test_file in test_files:

        start = time.perf_counter()

        try:

            module = load_module(test_file)

            result = module.run_test(args.submission_dir)

        except Exception as e:

            result = {
                "passed": False,
                "score": 0,
                "max_score": 0,
                "message": str(e),
                "model_output": None,
            }

        duration = int(
            (time.perf_counter() - start) * 1000
        )

        result["name"] = test_file.stem

        result["duration_ms"] = duration

        results["tests"].append(result)

        results["total_score"] += result["score"]

        results["max_score"] += result["max_score"]

    if results["total_score"] == results["max_score"]:

        results["status"] = "passed"

    elif results["total_score"] == 0:

        results["status"] = "failed"

    else:

        results["status"] = "partial"

    with open(args.output, "w", encoding="utf-8") as f:

        json.dump(
            results,
            f,
            ensure_ascii=False,
            indent=2
        )

    return 0 if results["status"] == "passed" else 1


if __name__ == "__main__":

    sys.exit(main())