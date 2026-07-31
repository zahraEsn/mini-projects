import sys


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
        input_text="این یک نمونه آزمایشی است."
        result = evaluator.evaluate(input_text)

        required_fields = [
            "score",
            "comments",
            "issues",
            "summary"
        ]

        for field in required_fields:

            if not hasattr(result, field):

                return {
                    "passed": False,
                    "score": 0,
                    "max_score": 10,
                    "message": f"فیلد '{field}' در خروجی وجود ندارد.",
                    "model_output": _safe_dump(result)
                }

        return {
            "passed": True,
            "score": 10,
            "max_score": 10,
            "message": "ساختار خروجی صحیح است.",
            "model_output": _safe_dump(result)
        }

    except Exception as e:

        return {
            "passed": False,
            "score": 0,
            "max_score": 10,
            "message": str(e),
            "model_output": _safe_dump(result)
        }