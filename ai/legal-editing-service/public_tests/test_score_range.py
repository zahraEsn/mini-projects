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


        score = result.score

        if not isinstance(score, (int, float)):

            return {
                "passed": False,
                "score": 0,
                "max_score": 10,
                "message": "score باید عدد باشد.",
                "model_output": _safe_dump(result)
            }

        if not (0 <= score <= 1):

            return {
                "passed": False,
                "score": 0,
                "max_score": 10,
                "message": "score باید بین 0 و 1 باشد.",
                "model_output": _safe_dump(result)
            }

        return {
            "passed": True,
            "score": 10,
            "max_score": 10,
            "message": "score معتبر است.",
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