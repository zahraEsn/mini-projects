import json
import logging
import os
import re
from collections import Counter
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)


class WritingIssue(BaseModel):
    incorrect_text: str
    correct_text: str
    issue_type: str
    explanation: str
    context: str


class WritingSummary(BaseModel):
    total_issues: int = 0
    by_type: Dict[str, int] = Field(default_factory=dict)


class ClarityWritingAnalysis(BaseModel):
    score: float = Field(ge=0, le=1)
    comments: str
    issues: List[WritingIssue] = Field(default_factory=list)
    summary: WritingSummary = Field(default_factory=WritingSummary)


# --------------------------------------------------------------------------- #
# Internal models for "strict" validation of raw LLM answers (without summary field,
# because we always build the summary ourselves from issues and never leave it to the model).
# --------------------------------------------------------------------------- #
class _LLMIssueStrict(BaseModel):
    incorrect_text: str
    correct_text: str
    issue_type: str
    explanation: str
    context: str


class _LLMAnalysisStrict(BaseModel):
    score: float = Field(ge=0, le=1)
    comments: str
    issues: List[_LLMIssueStrict] = Field(default_factory=list)


load_dotenv()


# Basic error types that must be supported.
# The model is allowed to report other types; these are for prompt guidance only.
BASE_ISSUE_TYPES = [
    "املاء",
    "علائم_نگارشی",
]

_SENTENCE_END_PUNCT = (".", "؟", "!", "…")

_JSON_SCHEMA_HINT = """
خروجی باید دقیقاً یک شیء JSON معتبر با این ساختار باشد (بدون هیچ متن اضافه، بدون Markdown، بدون توضیح خارج از JSON):

{
  "score": <عدد اعشاری بین 0 و 1>,
  "comments": "<توضیح کوتاه درباره کیفیت کلی نگارش متن>",
  "issues": [
    {
      "incorrect_text": "<بخش نادرست>",
      "correct_text": "<شکل صحیح>",
      "issue_type": "<نوع خطا، مثلا املاء یا علائم_نگارشی>",
      "explanation": "<توضیح کوتاه علت خطا>",
      "context": "<تکه‌ای از متن اصلی که خطا در آن دیده می‌شود>"
    }
  ]
}

توجه: فیلد summary را در خروجی خودت وارد نکن؛ فقط score، comments و issues کافی است،
چون summary به صورت خودکار از روی issues محاسبه می‌شود.
"""

_SYSTEM_PROMPT = f"""شما یک ویراستار حقوقی خبره و دقیق هستید که وظیفه‌اش بررسی نگارشی و املایی
متون آرا و تصمیمات قضایی فارسی است.

وظیفه شما فقط «شناسایی و گزارش» اشکالات است، نه بازنویسی، اصلاح، تلخیص یا خلاصه‌سازی متن.

نکات مهم:
- متن ورودی را تغییر نده و فقط آن را تحلیل کن.
- فقط خطاهایی را گزارش کن که واقعاً در متن وجود دارند (از گزارش خطای ساختگی یا تخمینی خودداری کن).
- تلاش کن هیچ خطای واقعی موجود در متن از قلم نیفتد.
- برای هر خطا حتما این موارد را دقیق و مرتبط با همان خطا مشخص کن:
  متن نادرست، شکل صحیح آن، نوع خطا، دلیل کوتاه خطا، و بخشی از متن اصلی که خطا در آن رخ داده (context).
- نیم‌فاصله (نویسهٔ ZWNJ): بررسی کن که پیشوندها/پسوندهای زیر با نیم‌فاصله از جزء اصلی کلمه جدا شده باشند
  و نه به‌صورت چسبیده یا با فاصلهٔ کامل:
  «می‌»، «نمی‌»، «‌ها»، «‌های»، «‌تر»، «‌ترین»، «‌ای»، «‌گونه»، «‌کننده»
  مثال خطا: «هیچگونه» ← صحیح: «هیچ‌گونه» / «میدهد» ← صحیح: «می‌دهد» / «کتابها» ← صحیح: «کتاب‌ها»
  این نوع خطا را با issue_type = "علائم_نگارشی" گزارش کن.

- همزه: بررسی کن کلماتی که باید با همزه نوشته شوند به‌درستی همزه‌دار باشند، نه ساده‌شده:
  مثال: «موثر» ← صحیح: «مؤثر» / «مسئول» یا «مسؤول» بسته به سیاق رسمی حقوقی /
  «رئیس» نه «رییس» / «سئوال» ← «سؤال»
  این نوع خطا را با issue_type = "املاء" گزارش کن.
- بررسی کن که هر جمله (و به‌ویژه انتهای کل متن) با نشانهٔ پایانی مناسب (نقطه، علامت سؤال یا 
  تعجب) تمام شده باشد؛  نبود این نشانه را به‌عنوان خطای علائم_نگارشی گزارش کن.
- انواع خطای پایه که باید در صورت وجود شناسایی شوند: {", ".join(BASE_ISSUE_TYPES)}.
  در صورت نیاز می‌توانی انواع دیگری از خطا (مثلا دستوری، ابهام، تکرار) را هم با نام مناسب گزارش کنی.
- مقدار score باید بازتاب‌دهنده کیفیت کلی نگارش متن باشد: هرچه خطاهای کمتر و جزئی‌تر، عدد نزدیک‌تر به 1؛
  هرچه خطاهای بیشتر و جدی‌تر، عدد نزدیک‌تر به 0.
- در اجراهای مختلف روی یک متن یکسان، سعی کن خروجی تا حد امکان پایدار و سازگار باشد
  (به همین دلیل با دقت و بر اساس شواهد متنی تصمیم بگیر، نه به صورت تصادفی).
- اگر متن ورودی خالی یا فاقد محتوای قابل بررسی بود، فهرست issues را خالی برگردان و score را 1.0 قرار بده.

{_JSON_SCHEMA_HINT}
"""

# JSON schema for response_format of type json_schema. Some OpenAI-compatible providers
# do not support this mode; in that case we automatically switch to json_object
# mode (which has wider support) (see _looks_like_unsupported_response_format).
_LLM_JSON_SCHEMA = {
    "name": "clarity_writing_analysis",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "score": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "description": "کیفیت نگارشی کلی متن؛ ۱ یعنی بدون خطا، ۰ یعنی کیفیت بسیار ضعیف.",
            },
            "comments": {
                "type": "string",
                "description": "توضیح کوتاه درباره کیفیت کلی نگارش متن.",
            },
            "issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "incorrect_text": {"type": "string"},
                        "correct_text": {"type": "string"},
                        "issue_type": {
                            "type": "string",
                            "description": "نوع خطا، معمولا یکی از 'املاء' یا 'علائم_نگارشی'، اما در صورت لزوم می‌تواند نوع دیگری باشد ('دستور_زبان' یا 'واژگان' یا 'سبک_حقوقی').",
                        },
                        "explanation": {"type": "string"},
                        "context": {"type": "string"},
                    },
                    "required": [
                        "incorrect_text",
                        "correct_text",
                        "issue_type",
                        "explanation",
                        "context",
                    ],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["score", "comments", "issues"],
        "additionalProperties": False,
    },
}

# Keywords indicating that the provider does not support response_format
# value of type json_schema (error messages vary between providers,
# so a conservative, keyword-based detection is used).
_UNSUPPORTED_FORMAT_HINTS = (
    "response_format",
    "json_schema",
    "unsupported",
    "not supported",
    "unknown parameter",
    "invalid_request_error",
)


class ClarityWritingEvaluator:
    """
    LLM-based legal editing service.

    The class takes a court decision/judicial text, submits it to a large language model
    to identify spelling and grammar errors, and returns the result in the form of a validated
    object of type ClarityWritingAnalysis.

    This class never throws an Exception: in case of any error
    (connecting to LLM, invalid response, etc.), a valid and safe output (fallback) is returned.
    """

    def __init__(self):

        self.client = OpenAI(
            api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL"),
        )

        self.model = os.getenv("LLM_MODEL")

        self.temperature = float(
            os.getenv("LLM_TEMPERATURE", "0")
        )

        self.max_retries = int(os.getenv("LLM_MAX_RETRIES", "2"))

        # If the provider does not support response_format of type json_schema,
        # this flag is enabled and json_object is used for all other requests.
        self._use_plain_json_mode = False

    # ------------------------------------------------------------------ #
    # Public entry point
    # ------------------------------------------------------------------ #
    def evaluate(self, decision_text: str) -> ClarityWritingAnalysis:
        """
        Receives the text of the verdict and returns the result of the clarity analysis
        as a ClarityWritingAnalysis object.

        Parameters
        ----------
        decision_text : str
        The full text of the verdict or judicial decision
        
        Returns
        -------
        ClarityWritingAnalysis
        """

        if not isinstance(decision_text, str) or not decision_text.strip():
            return self._empty_input_result()

        last_error: Optional[str] = None

        total_attempts = self.max_retries + 1

        for attempt in range(total_attempts):

            try:

                raw_content = self._call_llm(decision_text)

                data = self._extract_json(raw_content)

                return self._to_analysis(data)

            except Exception as e:  # noqa: BLE001

                last_error = str(e)

                logger.warning(
                    "تلاش %s از %s برای فراخوانی LLM ناموفق بود: %s",
                    attempt + 1,
                    total_attempts,
                    last_error,
                )

                continue

        logger.error("تمام تلاش‌ها برای دریافت پاسخ معتبر از LLM ناموفق بود: %s", last_error)

        return self._fallback_result(last_error)

    # ------------------------------------------------------------------ #
    # Interaction with LLM
    # ------------------------------------------------------------------ #
    def _call_llm(self, decision_text: str) -> str:

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "متن رأی زیر را از نظر املایی و نگارشی بررسی کن و "
                    "خروجی را دقیقاً طبق ساختار JSON خواسته‌شده برگردان.\n\n"
                    "متن:\n"
                    f"{decision_text}"
                ),
            },
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                response_format=self._response_format(),
                messages=messages,
            )
        except Exception as exc:  # noqa: BLE001
            # If the provider doesn't support json_schema, we retry 
            # the same request once with the simpler json_object 
            # (without spending another # full attempt on the outer retry loop).
            if not self._use_plain_json_mode and self._looks_like_unsupported_response_format(exc):

                logger.warning(
                    "به نظر می‌رسد provider از response_format=json_schema پشتیبانی نمی‌کند؛ "
                    "سوییچ به json_object. جزئیات: %s",
                    exc,
                )

                self._use_plain_json_mode = True

                response = self.client.chat.completions.create(
                    model=self.model,
                    temperature=self.temperature,
                    response_format=self._response_format(),
                    messages=messages,
                )
            else:
                raise

        content = response.choices[0].message.content

        if not content:
            raise ValueError("پاسخ خالی از مدل زبانی دریافت شد.")

        return content

    def _response_format(self) -> Dict[str, Any]:
        """
        Most OpenAI-compatible providers support json_object, but
        only some of them support json_schema (a more rigorous, structured output).
        The more rigorous mode is tried first; if it fails,
        _call_llm automatically switches to json_object.
        """

        if self._use_plain_json_mode:
            return {"type": "json_object"}

        return {"type": "json_schema", "json_schema": _LLM_JSON_SCHEMA}

    @staticmethod
    def _looks_like_unsupported_response_format(exc: Exception) -> bool:

        message = str(exc).lower()

        return any(hint in message for hint in _UNSUPPORTED_FORMAT_HINTS)

    # ------------------------------------------------------------------ #
    # Response processing and validation
    # ------------------------------------------------------------------ #
    @staticmethod
    def _extract_json(raw_content: str) -> Dict[str, Any]:
        """
        Extracts JSON from the model's text response, even if it is enclosed in ```json
        or there is additional text before/after it.
        """

        text = raw_content.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        fence_match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if fence_match:
            try:
                return json.loads(fence_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        first_brace = text.find("{")
        last_brace = text.rfind("}")

        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            candidate = text[first_brace : last_brace + 1]
            return json.loads(candidate)

        raise ValueError("امکان استخراج JSON معتبر از پاسخ مدل وجود نداشت.")

    def _to_analysis(self, data: Dict[str, Any]) -> ClarityWritingAnalysis:
        """
        First, the entire response is tried to be validated in strict pydantic. If only a few items of the issues have problems (e.g., a missing field), then instead of discarding the entire response and spending another attempt, in "lenient" mode, only those faulty items are discarded and the rest of the output is preserved.
        """

        try:
            strict = _LLMAnalysisStrict.model_validate(data)

            issues = [
                WritingIssue(**issue.model_dump()) for issue in strict.issues
            ]

            score = max(0.0, min(1.0, float(strict.score)))

            return ClarityWritingAnalysis(
                score=score,
                comments=strict.comments,
                issues=issues,
                summary=self._build_summary(issues),
            )

        except ValidationError:
            # At least one of the main items or fields did not match the schema;
            # We try to salvage as much as possible from the response in a flexible way.
            return self._to_analysis_lenient(data)

    def _to_analysis_lenient(self, data: Dict[str, Any]) -> ClarityWritingAnalysis:

        issues_raw = data.get("issues", []) or []

        issues: List[WritingIssue] = []

        for item in issues_raw:

            try:
                issues.append(
                    WritingIssue(
                        incorrect_text=str(item.get("incorrect_text", "")),
                        correct_text=str(item.get("correct_text", "")),
                        issue_type=str(item.get("issue_type", "")),
                        explanation=str(item.get("explanation", "")),
                        context=str(item.get("context", "")),
                    )
                )
            except (ValidationError, AttributeError):
                # Incomplete or invalid items are ignored to avoid corrupting the entire output.
                continue

        summary = self._build_summary(issues)

        score = data.get("score", 0.0)

        try:
            score = float(score)
        except (TypeError, ValueError):
            score = 0.0

        score = max(0.0, min(1.0, score))

        comments = str(data.get("comments", "") or "")

        return ClarityWritingAnalysis(
            score=score,
            comments=comments,
            issues=issues,
            summary=summary,
        )

    @staticmethod
    def _build_summary(issues: List[WritingIssue]) -> WritingSummary:
        """
        summary is always computed directly from issues to ensure that
        summary.total_issues and summary.by_type are always consistent with the list of issues
        (regardless of what the language model has produced for summary).
        """

        counter = Counter(issue.issue_type for issue in issues)

        return WritingSummary(
            total_issues=len(issues),
            by_type=dict(counter),
        )

    # ------------------------------------------------------------------ #
    # Special and safe modes
    # ------------------------------------------------------------------ #
    @staticmethod
    def _empty_input_result() -> ClarityWritingAnalysis:

        return ClarityWritingAnalysis(
            score=1.0,
            comments="متن ورودی خالی است و اشکال نگارشی برای بررسی وجود ندارد.",
            issues=[],
            summary=WritingSummary(total_issues=0, by_type={}),
        )

    @staticmethod
    def _fallback_result(error_message: Optional[str]) -> ClarityWritingAnalysis:
        """
        If the connection to the LLM fails or the response is repeatedly invalid,
        a valid (but conservative) output is returned instead of raising an Exception.
        """

        message = "خطا در دریافت یا پردازش پاسخ مدل زبانی."

        if error_message:
            message = f"{message} جزئیات: {error_message}"

        return ClarityWritingAnalysis(
            score=0.5,
            comments=message,
            issues=[],
            summary=WritingSummary(total_issues=0, by_type={}),
        )
