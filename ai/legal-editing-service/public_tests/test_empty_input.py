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

        result = evaluator.evaluate("")

        if result is None:

            return {
                "passed": False,
                "score": 0,
                "max_score": 10,
                "message": "خروجی نباید None باشد.",
                "model_output": None
            }

        if not hasattr(result, "issues"):

            return {
                "passed": False,
                "score": 0,
                "max_score": 10,
                "message": "فیلد issues در خروجی وجود ندارد.",
                "model_output": _safe_dump(result)
            }

        return {
            "passed": True,
            "score": 10,
            "max_score": 10,
            "message": "ورودی خالی بدون خطا مدیریت شد.",
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