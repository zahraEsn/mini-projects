import sys
from collections import Counter


def _safe_dump(obj):
    """خروجی مدل (result) را برای درج در results.json به دیکشنری/مقدار قابل JSON تبدیل می‌کند."""
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump()
        except Exception:
            return str(obj)
    return obj


def run_test(submission_dir):

    result = None

    try:

        if submission_dir not in sys.path:
            sys.path.insert(0, submission_dir)

        from ClarityWritingEvaluator import ClarityWritingEvaluator

        evaluator = ClarityWritingEvaluator()

        input_text="این یک نمونه آزمایشی است که با ان از سازکاری خلاسه بابقیه موارد اتمینان هاصل شود"
        result = evaluator.evaluate(input_text)

        summary = result.summary

        if isinstance(summary, dict):
            total = summary.get("total_issues", 0)
            by_type = summary.get("by_type", {})
        else:
            total = summary.total_issues
            by_type = summary.by_type

        if total != len(result.issues):

            return {
                "passed": False,
                "score": 0,
                "max_score": 15,
                "message": "summary.total_issues با تعداد issues مطابقت ندارد.",
                "model_output": _safe_dump(result)
            }

        counter = Counter()

        for issue in result.issues:

            if isinstance(issue, dict):
                counter[issue["issue_type"]] += 1
            else:
                counter[issue.issue_type] += 1

        if dict(counter) != dict(by_type):

            return {
                "passed": False,
                "score": 0,
                "max_score": 15,
                "message": "summary.by_type با لیست issues سازگار نیست.",
                "model_output": _safe_dump(result)
            }

        return {
            "passed": True,
            "score": 15,
            "max_score": 15,
            "message": "summary با issues سازگار است.",
            "model_output": _safe_dump(result)
        }

    except Exception as e:

        return {
            "passed": False,
            "score": 0,
            "max_score": 15,
            "message": str(e),
            "model_output": _safe_dump(result)
        }