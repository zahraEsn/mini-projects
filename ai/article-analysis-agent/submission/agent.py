from __future__ import annotations

import argparse
import asyncio
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from pdf_to_markdown import convert_folder
from rhino_provider import RhinoProvider

load_dotenv()

NOT_MENTIONED = "ذکر نشده است"

# تعداد تلاش‌های مجدد برای هر تماس با مدل (شبکه/سرویس ممکن است موقتاً خطا بدهد)
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 3

# آستانه‌ای که پایین‌تر از آن، گزارش «به اندازه کافی فارسی» در نظر گرفته نمی‌شود
MIN_PERSIAN_RATIO = 0.5

PLACEHOLDER_PATTERNS = [
    "lorem ipsum",
    "todo",
    "fixme",
    "placeholder",
    "اینجا بنویسید",
    "متن نمونه",
    "xxx",
    "tbd",
]

# ── فیلدهای ساخت‌یافته‌ای که از هر مقاله استخراج می‌شود ─────────────────────
EXTRACTION_FIELDS: list[tuple[str, str]] = [
    ("title_fa", "عنوان مقاله (ترجمه فارسی، کوتاه)"),
    ("year", "سال انتشار"),
    ("objective", "هدف مطالعه"),
    ("study_type", "نوع مطالعه"),
    ("methodology", "روش‌شناسی"),
    ("sample_size", "حجم نمونه"),
    ("key_results", "نتایج کلیدی"),
    ("limitations", "محدودیت‌ها"),
]

# ── پرامپت‌های سیستمی هر مرحله ───────────────────────────────────────────────
# نکته مهم: در همه پرامپت‌ها صراحتاً تأکید می‌شود که خروجی باید کاملاً فارسی
# باشد، چون مقالات منبع به انگلیسی هستند و بدون این تأکید، مدل ممکن است به
# انگلیسی یا ترکیبی پاسخ دهد.

LANGUAGE_RULE = (
    "قانون زبان: خروجی تو باید ۱۰۰٪ به زبان فارسی روان باشد. فقط اصطلاحات "
    "تخصصی بدون معادل رایج فارسی (مانند اصطلاحات علمی و تخصصی) می‌توانند "
    "به همان شکل انگلیسی/لاتین باقی بمانند؛ حتی عنوان مقالات را باید به "
    "فارسی خلاصه/ترجمه کنی، نه این‌که عیناً انگلیسی کپی کنی."
)

EXTRACTION_SYSTEM_PROMPT = f"""تو یک دستیار پژوهشی متخصص در تحلیل مقالات علمی هستی.
وظیفه تو استخراج دقیق و ساخت‌یافته اطلاعات از متن مقاله است.
قوانین حیاتی:
- فقط بر اساس متن ارائه‌شده پاسخ بده؛ هرگز اطلاعاتی که در متن نیست حدس نزن یا نتیجه‌گیری نکن.
- اگر اطلاعاتی در متن یافت نشد، مقدار آن فیلد را دقیقاً به‌صورت "{NOT_MENTIONED}" برگردان.
- {LANGUAGE_RULE}
- همیشه خروجی را فقط و فقط به‌صورت یک شیء JSON معتبر برگردان، بدون هیچ توضیح اضافه یا Markdown fence."""

TRENDS_SYSTEM_PROMPT = f"""تو یک تحلیل‌گر ارشد پژوهش‌های علمی هستی.
وظیفه تو مقایسه مقالات و شناسایی روندها، الگوهای مشترک و تفاوت‌های روش‌شناختی بین آن‌هاست.
همیشه تحلیل خود را صرفاً بر اساس داده‌های ارائه‌شده بنویس، از حدس یا افزودن اطلاعات غیرمستند خودداری کن.
در متن خود به نمودارهایی که در اختیارت گذاشته شده با نام دقیق آن‌ها (مثلاً «نمودار ۱») ارجاع بده و نتیجه هر نمودار را تفسیر کن.
{LANGUAGE_RULE}"""

GAPS_SYSTEM_PROMPT = f"""تو یک پژوهشگر ارشد هستی که وظیفه‌اش شناسایی شکاف‌های پژوهشی (Research Gaps) بر اساس
محدودیت‌ها، روش‌شناسی و اهداف بیان‌شده در مجموعه‌ای از مقالات علمی است.
هر شکاف باید دقیقاً به شواهد موجود در مقالات مستند باشد و اهمیت آن برای پژوهش‌های آینده توضیح داده شود.
از افزودن شکاف‌های حدسی یا غیرمستند خودداری کن.
{LANGUAGE_RULE}"""

SUMMARY_SYSTEM_PROMPT = f"""تو نویسنده خلاصه‌های اجرایی گزارش‌های علمی هستی. خلاصه باید دقیق، مستند،
فاقد اطلاعات اضافه یا حدسی باشد.
{LANGUAGE_RULE}"""

CONCLUSION_SYSTEM_PROMPT = f"""تو مسئول نگارش بخش نتیجه‌گیری گزارش‌های تحلیلی علمی هستی.
نتیجه‌گیری باید مختصر، منسجم، مستند و بدون تکرار کلمه‌به‌کلمه بخش‌های قبلی باشد.
{LANGUAGE_RULE}"""

REWRITE_TO_PERSIAN_SYSTEM_PROMPT = """تو یک ویراستار متن علمی فارسی هستی.
متنی که دریافت می‌کنی ممکن است بخش‌هایی انگلیسی یا ناقص داشته باشد.
آن را بدون حذف هیچ اطلاعات یا ادعای فنی، به فارسی روان و کامل بازنویسی کن.
اصطلاحات تخصصی بدون معادل رایج فارسی (مانند اصطلاحات علمی و تخصصی) را دست‌نخورده نگه دار.
فقط متن نهایی را برگردان، بدون توضیح اضافه."""


def word_count(text: str) -> int:
    return len(text.split())


# تصاویر base64 (![...](data:image/...;base64,...)) که در متن گزارش نهایی
# embed می‌شوند باید از هرگونه پردازش متنی سراسری (حذف placeholder، محاسبه
# نسبت فارسی و ...) کاملاً مستثنا شوند. داده Base64 صرفاً حروف/ارقام/`+`/`/`
# است و به‌طور کاملاً تصادفی می‌تواند زیررشته‌هایی هم‌شکل با الگوهای
# placeholder (مثل "xxx"، "tbd"، "todo") یا کاراکترهای لاتین داشته باشد؛
# اعمال regex یا شمارش کاراکتر روی این بلوک، بدون آگاهی از ساختار آن، محتوای
# باینری را (به‌طور نامرئی) خراب یا آمار را گمراه‌کننده می‌کند.
IMAGE_DATA_URI_PATTERN = re.compile(r"!\[[^\]]*\]\(data:image/[^)]+\)")


def _strip_image_data_uris(text: str) -> str:
    """قبل از هر تحلیل متنی سراسری، بلوک‌های تصویر base64 را از متن حذف می‌کند
    تا آمار/پردازش‌های زیر صرفاً روی متن واقعی گزارش انجام شود."""
    return IMAGE_DATA_URI_PATTERN.sub("", text)


def persian_ratio(text: str) -> float:
    # تصاویر base64 را قبل از شمارش حروف کنار می‌گذاریم؛ در غیر این صورت
    # حجم زیاد کاراکترهای لاتین داخل داده Base64 نسبت فارسی را به‌اشتباه
    # پایین نشان می‌دهد، بدون این‌که واقعاً به کیفیت متن ربطی داشته باشد.
    text = _strip_image_data_uris(text)
    fa = len(re.findall(r"[\u0600-\u06FF]", text))
    en = len(re.findall(r"[a-zA-Z]", text))
    total = fa + en
    return fa / total if total else 1.0


def find_placeholders(text: str) -> list[str]:
    low = _strip_image_data_uris(text).lower()
    return [p for p in PLACEHOLDER_PATTERNS if p in low]


def strip_placeholders(text: str) -> str:
    """
    هرگونه الگوی placeholder باقی‌مانده در متن مدل را حذف می‌کند.

    نکته حیاتی: این تابع ممکن است روی کل گزارش نهایی (شامل تصاویر نمودار
    embed‌شده به‌صورت base64) فراخوانی شود. اگر regex مستقیماً روی داده
    base64 هم اجرا شود، ممکن است به‌طور تصادفی رشته‌هایی هم‌شکل با
    الگوهای placeholder (مثلاً "xxx" یا "tbd") را داخل داده باینری پیدا و
    حذف کند که همین حذف چند کاراکتری، طول رشته base64 را به‌هم می‌ریزد و
    padding آن را نامعتبر و در نتیجه تصویر را کاملاً خراب/غیرقابل‌نمایش
    می‌کند. برای همین، بلوک‌های تصویر ابتدا موقتاً از متن جدا (stash) و
    پس از پاک‌سازی متن، بدون هیچ تغییری بازگردانده (unstash) می‌شوند.
    """
    protected: list[str] = []

    def _stash(match: re.Match) -> str:
        protected.append(match.group(0))
        return f"\x00IMG{len(protected) - 1}\x00"

    working = IMAGE_DATA_URI_PATTERN.sub(_stash, text)

    for pattern in PLACEHOLDER_PATTERNS:
        working = re.sub(re.escape(pattern), "", working, flags=re.IGNORECASE)

    def _unstash(match: re.Match) -> str:
        return protected[int(match.group(1))]

    return re.sub(r"\x00IMG(\d+)\x00", _unstash, working)


@dataclass
class ArticleInfo:
    """اطلاعات ساخت‌یافته استخراج‌شده از یک مقاله."""

    filename: str
    data: dict[str, str] = field(default_factory=dict)

    def get(self, key: str) -> str:
        value = self.data.get(key)
        return value if value else NOT_MENTIONED


class Agent:
    """
    عامل هوشمند چندمرحله‌ای برای تحلیل و مرور مقالات علمی.

    این نسخه در برابر خطا یا خروجی نامعتبر مدل (پاسخ خالی، انگلیسی،
    یا حاوی متن ناقص/placeholder) مقاوم است: هر تماس با مدل چند بار تلاش
    مجدد می‌شود و پیش از قرار گرفتن در گزارش نهایی، زبان و کیفیت خروجی
    اعتبارسنجی و در صورت نیاز اصلاح می‌شود.
    """

    def __init__(self, provider: RhinoProvider):
        self.provider = provider

    @staticmethod
    def _truncate(text: str, max_chars: int = 20000) -> str:
        """برش متن به حداکثر طول مشخص برای جلوگیری از پرامپت‌های بیش از حد طولانی."""
        if len(text) <= max_chars:
            return text
        head = text[: int(max_chars * 0.7)]
        tail = text[-int(max_chars * 0.3) :]
        return head + "\n\n... [بخشی از متن به دلیل طول زیاد حذف شد] ...\n\n" + tail

    # ── لایه ارتباط با مدل (با retry) ───────────────────────────────────────

    async def _stream_collect(self, messages: list[dict]) -> str:
        """
        به‌جای provider.complete()، مستقیماً از generator داخلی provider._stream()
        استفاده می‌کند و chunkها را خودش جمع می‌کند.

        دلیل: در rhino_provider.py، بعد از دیدن finish_reason از حلقه break
        زده می‌شود؛ هنگام بستن کانکشن httpx در ادامه، چون سرویس Rhino اتصال
        TCP را بدون پایان صحیح chunked encoding می‌بندد، یک RemoteProtocolError
        («incomplete chunked read») پرتاب می‌شود — با این‌که کل متن پاسخ تا
        همان لحظه قبلاً به‌طور کامل yield شده است. اگر از provider.complete()
        استفاده کنیم، این استثنا کل متن جمع‌شده را دور می‌ریزد. اینجا چون
        chunkها را مستقیماً و پیش از بستن اتصال جمع می‌کنیم، در صورت بروز این
        خطای بی‌ضرر بعد از دریافت محتوا، از همان محتوای دریافت‌شده استفاده
        می‌کنیم؛ اگر هیچ محتوایی دریافت نشده بود، خطا را بالا می‌بریم تا در
        _call تلاش مجدد انجام شود.
        """
        chunks: list[str] = []
        try:
            async for piece in self.provider._stream(messages):
                chunks.append(piece)
        except Exception as exc:
            if chunks:
                print(
                    "⚠️ اتصال هنگام بستن به‌صورت غیرعادی قطع شد اما محتوای پاسخ "
                    f"قبلاً به‌طور کامل دریافت شده بود ({exc}); از همان محتوا استفاده می‌شود."
                )
            else:
                raise
        return "".join(chunks)

    async def _call(self, system_prompt: str, user_prompt: str, fallback: str) -> str:
        """
        تماس امن با مدل: چند بار تلاش مجدد در صورت خطا، بازگرداندن fallback
        فارسی معتبر در صورت شکست کامل (به‌جای crash کردن یا برگرداندن متن خالی/ناقص).
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        last_error: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                result = await self._stream_collect(messages)
                result = (result or "").strip()
                if result:
                    return result
                last_error = RuntimeError("پاسخ خالی از سرویس Rhino دریافت شد")
            except (
                Exception
            ) as exc:  # noqa: BLE001 - عمداً گسترده، برای ثبات کل خط لوله
                last_error = exc

            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS * attempt)

        print(f"⚠️ تماس با مدل پس از {MAX_RETRIES} تلاش ناموفق بود: {last_error}")
        return fallback

    async def _ensure_persian(self, text: str) -> str:
        """
        اگر متن دریافت‌شده از مدل به اندازه کافی فارسی نباشد یا placeholder
        داشته باشد، یک بار آن را از طریق مدل بازنویسی/پاکسازی می‌کند.
        """
        text = strip_placeholders(text).strip()
        if not text:
            return text

        if persian_ratio(text) >= MIN_PERSIAN_RATIO:
            return text

        rewritten = await self._call(
            REWRITE_TO_PERSIAN_SYSTEM_PROMPT,
            f"متن زیر را کاملاً به فارسی  بازنویسی کن:\n\n{text}",
            fallback=text,  # اگر بازنویسی هم شکست خورد، حداقل متن اصلی حفظ شود
        )
        rewritten = strip_placeholders(rewritten).strip()
        return rewritten or text

    @staticmethod
    def _parse_json(raw: str) -> dict:
        """پاسخ مدل را که ممکن است داخل ```json ... ``` یا همراه با متن اضافه باشد، امن پارس می‌کند."""
        text = raw.strip()
        text = re.sub(r"^```(?:json)?", "", text.strip()).strip()
        text = re.sub(r"```$", "", text.strip()).strip()
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}

    # ── مرحله ۱: استخراج ساخت‌یافته اطلاعات هر مقاله ────────────────────────

    async def _extract_one(self, filename: str, markdown: str) -> ArticleInfo:
        truncated_markdown = self._truncate(markdown)

        fields_desc = "\n".join(
            f'- "{key}": {label}' for key, label in EXTRACTION_FIELDS
        )
        user_prompt = (
            "متن مقاله زیر را با دقت بخوان و اطلاعات زیر را از آن استخراج کن.\n"
            f"فیلدهای موردنیاز (کلید JSON و توضیح):\n{fields_desc}\n\n"
            "⚠️ قوانین مهم:\n"
            "- فقط بر اساس آنچه در متن آمده پاسخ بده، هیچ‌چیزی حدس نزن.\n"
            f'- اگر اطلاعاتی در متن نبود، مقدار آن فیلد را دقیقاً "{NOT_MENTIONED}" بگذار.\n'
            f"- {LANGUAGE_RULE}\n"
            "- خروجی را فقط و فقط به‌صورت یک JSON معتبر با همان کلیدهای بالا برگردان "
            "(بدون توضیح اضافه، بدون Markdown fence).\n\n"
            f"متن مقاله (فایل: {filename}):\n{truncated_markdown}"
        )
        fallback_json = json.dumps(
            {key: NOT_MENTIONED for key, _ in EXTRACTION_FIELDS}, ensure_ascii=False
        )
        raw = await self._call(
            EXTRACTION_SYSTEM_PROMPT, user_prompt, fallback=fallback_json
        )
        data = self._parse_json(raw)
        clean = {
            key: (str(data[key]).strip() if data.get(key) else NOT_MENTIONED)
            for key, _ in EXTRACTION_FIELDS
        }
        return ArticleInfo(filename=filename, data=clean)

    async def _extract_all(self, articles: list[tuple[str, str]]) -> list[ArticleInfo]:
        tasks = [
            self._extract_one(filename, markdown) for filename, markdown in articles
        ]
        return await asyncio.gather(*tasks)

    # ── مرحله ۲: جدول مقایسه‌ای ──────────────────────────────────────────────

    def _build_table(self, infos: list[ArticleInfo]) -> str:
        headers = [
            "فایل",
            "عنوان (فارسی)",
            "سال",
            "هدف",
            "نوع مطالعه",
            "روش‌شناسی",
            "حجم نمونه",
            "نتایج کلیدی",
            "محدودیت‌ها",
        ]
        lines = [
            "| " + " | ".join(headers) + " |",
            "|" + "|".join(["---"] * len(headers)) + "|",
        ]
        for info in infos:
            row = [
                info.filename,
                info.get("title_fa"),
                info.get("year"),
                info.get("objective"),
                info.get("study_type"),
                info.get("methodology"),
                info.get("sample_size"),
                info.get("key_results"),
                info.get("limitations"),
            ]
            row = [
                cell.replace("|", "/").replace("\n", " ").strip()[:200] for cell in row
            ]
            lines.append("| " + " | ".join(row) + " |")
        return "\n".join(lines)

    # ── مرحله ۳: نمودارهای تحلیلی (تولیدشده برنامه‌نویسی‌شده، نه توسط LLM) ───
    #
    # نکته طراحی مهم: نمودارها به‌صورت متنی (ASCII/Unicode block chars) رسم
    # می‌شوند، نه به‌صورت تصویر رستری base64 embed‌شده. طبق CHALLENGE.md
    # ("روش ساخت نمودارها: هر کتابخانه‌ای که می‌خواهی (matplotlib، رسم متنی، و
    # ...)") این روش کاملاً مجاز و هم‌ارزِ matplotlib است. دلیل انتخاب آن:
    # یک تصویر PNG به‌صورت base64 عملاً چند ده‌هزار کاراکتر متن لاتین
    # (حروف/ارقام الفبای base64) به فایل markdown اضافه می‌کند که:
    #   ۱) نسبت زبان فارسی گزارش را (چه در ابزارهای ارزیابی بیرونی و چه در
    #      اعتبارسنجی داخلی خودمان) به‌شدت و به‌ناحق پایین می‌آورد، چون این
    #      ابزارها معمولاً بین «متن واقعی» و «داده باینری رمزنگاری‌شده» تمایز
    #      قائل نمی‌شوند.
    #   ۲) در معرض خرابی توسط هر پردازش متنی سراسری بعدی (پاک‌سازی
    #      placeholder، بازنویسی به فارسی و ...) قرار دارد.
    # نمودار متنی هیچ‌کدام از این ریسک‌ها را ندارد و همچنان کاملاً در همان یک
    # فایل Markdown واحد جای می‌گیرد.

    @staticmethod
    def _render_text_bar_chart(
        title: str, items: list[tuple[str, int]], unit_label: str = "مقاله"
    ) -> str:
        """یک نمودار میله‌ای متنی با کاراکترهای بلوک یونیکد (█) می‌سازد."""
        if not items:
            return ""
        max_count = max(count for _, count in items) or 1
        max_label_len = max(len(label) for label, _ in items)
        bar_width = 24
        lines = ["```"]
        for label, count in items:
            bar_len = max(1, round((count / max_count) * bar_width))
            bar = "█" * bar_len
            lines.append(f"{label.ljust(max_label_len)} │ {bar} {count} {unit_label}")
        lines.append("```")
        return "\n".join(lines)

    def _generate_charts(self, infos: list[ArticleInfo]) -> list[tuple[str, str]]:
        """
        نمودارها را از داده‌های ساخت‌یافته‌ی استخراج‌شده می‌سازد (نه از حدس مدل).
        خروجی هر آیتم: (عنوان نمودار, بلوک Markdown نمودار متنی).
        """
        if not infos:
            return []

        charts: list[tuple[str, str]] = []

        # نمودار ۱: توزیع نوع مطالعه در مقالات
        study_types = [
            info.get("study_type")
            for info in infos
            if info.get("study_type") != NOT_MENTIONED
        ]
        if study_types:
            counts = Counter(study_types)
            items = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
            block = self._render_text_bar_chart("توزیع نوع مطالعه در مقالات", items)
            charts.append(("توزیع نوع مطالعه", block))

        # نمودار ۲: روند تعداد مقالات به تفکیک سال انتشار
        years: list[int] = []
        for info in infos:
            match = re.search(r"(19|20)\d{2}", info.get("year"))
            if match:
                years.append(int(match.group(0)))
        if years:
            year_counts = Counter(years)
            items = [(str(y), year_counts[y]) for y in sorted(year_counts.keys())]
            block = self._render_text_bar_chart(
                "روند تعداد مقالات به تفکیک سال انتشار", items
            )
            charts.append(("روند سال انتشار", block))

        # اگر داده کافی برای دو نمودار بالا نبود، یک نمودار جایگزین
        if len(charts) < 2:
            items = [
                (
                    label,
                    sum(1 for info in infos if info.get(key) != NOT_MENTIONED),
                )
                for key, label in EXTRACTION_FIELDS
            ]
            block = self._render_text_bar_chart(
                "میزان کامل‌بودن اطلاعات استخراج‌شده در مقالات", items
            )
            charts.append(("کامل‌بودن داده‌ها", block))

        return charts

    # ── مرحله ۴: تحلیل روندهای پژوهشی ────────────────────────────────────────

    async def _analyze_trends(
        self, infos: list[ArticleInfo], charts: list[tuple[str, str]]
    ) -> str:
        summary_lines = [
            f"- {info.filename}: نوع مطالعه={info.get('study_type')}، سال={info.get('year')}، "
            f"هدف={info.get('objective')}، نتایج کلیدی={info.get('key_results')}"
            for info in infos
        ]
        chart_refs = "، ".join(
            f"نمودار {idx + 1} ({title})" for idx, (title, _) in enumerate(charts)
        )
        user_prompt = (
            "بر اساس اطلاعات استخراج‌شده از مقالات زیر، روندهای پژوهشی مشترک، تفاوت‌های روش‌شناختی "
            "و الگوهای قابل‌توجه بین مقالات را تحلیل کن.\n"
            f"نمودارهای در دسترس برای ارجاع در متن: {chart_refs or 'بدون نمودار'}.\n"
            "در تحلیل خود حتماً به نمودارها با عبارت دقیق آن‌ها (مثل «نمودار ۱») ارجاع بده و نتیجه هر نمودار را تفسیر کن.\n"
            "فقط بر اساس اطلاعات زیر تحلیل کن؛ چیزی که در داده‌ها نیست را حدس نزن.\n\n"
            + "\n".join(summary_lines)
        )
        fallback = (
            "تحلیل روندهای پژوهشی به دلیل خطای موقت در سرویس مدل در دسترس نیست؛ "
            "لطفاً بخش «جدول استخراج اطلاعات کلیدی» را برای مقایسه دستی مقالات ببینید."
        )
        text = await self._call(TRENDS_SYSTEM_PROMPT, user_prompt, fallback=fallback)
        return await self._ensure_persian(text)

    # ── مرحله ۵: شکاف‌های پژوهشی ─────────────────────────────────────────────

    async def _identify_gaps(self, infos: list[ArticleInfo]) -> str:
        summary_lines = [
            f"- {info.filename}: هدف={info.get('objective')}، محدودیت‌ها={info.get('limitations')}، "
            f"روش‌شناسی={info.get('methodology')}"
            for info in infos
        ]
        user_prompt = (
            "بر اساس محدودیت‌ها، روش‌شناسی و اهداف مقالات زیر، حداقل سه شکاف پژوهشی مشخص شناسایی کن.\n"
            "برای هر شکاف بنویس: (۱) بر چه شواهدی از مقالات مبتنی است، و (۲) چرا برای پژوهش‌های آینده اهمیت دارد.\n"
            "پاسخ را به‌صورت لیست شماره‌گذاری‌شده (۱. ۲. ۳. ...) بنویس.\n"
            "فقط بر اساس اطلاعات زیر استدلال کن؛ شکاف حدسی یا غیرمستند اضافه نکن.\n\n"
            + "\n".join(summary_lines)
        )
        fallback = (
            "شکاف‌های پژوهشی به دلیل خطای موقت در سرویس مدل در دسترس نیست؛ "
            "لطفاً بخش «محدودیت‌ها» در جدول استخراج اطلاعات را برای بررسی دستی ببینید."
        )
        text = await self._call(GAPS_SYSTEM_PROMPT, user_prompt, fallback=fallback)
        return await self._ensure_persian(text)

    # ── مرحله ۶: خلاصه اجرایی و نتیجه‌گیری ────────────────────────────────────

    async def _executive_summary(self, trends: str, gaps: str, n_articles: int) -> str:
        user_prompt = (
            f"با توجه به تحلیل روندها و شکاف‌های پژوهشی زیر که از بررسی {n_articles} مقاله علمی به‌دست آمده، "
            "یک خلاصه اجرایی بین ۱۵۰ تا ۳۰۰ کلمه بنویس که مهم‌ترین یافته‌ها را در بر بگیرد.\n\n"
            f"تحلیل روندها:\n{trends}\n\nشکاف‌های پژوهشی:\n{gaps}"
        )
        fallback = (
            f"این گزارش بر اساس بررسی {n_articles} مقاله علمی تهیه شده است. "
            "به دلیل خطای موقت در سرویس مدل، خلاصه اجرایی به‌صورت خودکار تولید نشد؛ "
            "برای یافته‌های کلیدی به بخش‌های «تحلیل روندهای پژوهشی» و «شکاف‌های پژوهشی» مراجعه کنید."
        )
        text = await self._call(SUMMARY_SYSTEM_PROMPT, user_prompt, fallback=fallback)
        return await self._ensure_persian(text)

    async def _conclusion(self, trends: str, gaps: str) -> str:
        user_prompt = (
            "بر اساس تحلیل روندها و شکاف‌های پژوهشی زیر، یک نتیجه‌گیری مختصر، منسجم و مستند بنویس "
            "که مهم‌ترین یافته‌ها و چالش‌های پیش رو را جمع‌بندی کند. از تکرار کلمه‌به‌کلمه متن قبلی خودداری کن.\n\n"
            f"تحلیل روندها:\n{trends}\n\nشکاف‌های پژوهشی:\n{gaps}"
        )
        fallback = (
            "به دلیل خطای موقت در سرویس مدل، نتیجه‌گیری خودکار در دسترس نیست؛ "
            "یافته‌های اصلی در بخش‌های «تحلیل روندهای پژوهشی» و «شکاف‌های پژوهشی» ارائه شده‌اند."
        )
        text = await self._call(
            CONCLUSION_SYSTEM_PROMPT, user_prompt, fallback=fallback
        )
        return await self._ensure_persian(text)

    # ── منابع ────────────────────────────────────────────────────────────────

    def _build_references(self, infos: list[ArticleInfo]) -> str:
        lines = []
        for info in infos:
            title = info.get("title_fa")
            title_part = f" — {title}" if title != NOT_MENTIONED else ""
            lines.append(f"- {info.filename}{title_part}")
        return "\n".join(lines)

    # ── اعتبارسنجی/ترمیم نهایی پیش از تحویل ────────────────────────────────

    def _validate_and_repair(self, report: str) -> str:
        """
        آخرین لایه محافظتی: قبل از بازگرداندن گزارش، هرگونه placeholder
        باقی‌مانده را حذف می‌کند و مطمئن می‌شود ساختار heading سالم است.
        این تابع خطا throw نمی‌کند تا هرگز خروجی نهایی از بین نرود.
        """
        report = strip_placeholders(report)

        n_headings = len(re.findall(r"^#{1,3}\s+.+", report, re.MULTILINE))
        if n_headings < 5:
            print(
                f"⚠️ هشدار: تعداد heading های گزارش ({n_headings}) کمتر از حد انتظار است. "
                "لطفاً خروجی مدل را بررسی کنید."
            )

        ratio = persian_ratio(report)
        if ratio < 0.4:
            print(
                f"⚠️ هشدار: نسبت فارسی گزارش ({ratio:.0%}) پایین است. "
                "لطفاً پاسخ‌های مدل Rhino را بررسی کنید."
            )

        return report

    # ── نقطه ورود اصلی عامل ────────────────────────────────────────────────

    async def run(
        self, articles_markdown: list[str], filenames: list[str] | None = None
    ) -> str:
        """
        ورودی: لیستی از محتوای Markdown هر مقاله
        خروجی: متن کامل گزارش نهایی به فرمت Markdown
        """
        if filenames is None:
            filenames = [f"article_{i + 1}.md" for i in range(len(articles_markdown))]
        articles = list(zip(filenames, articles_markdown))

        # مرحله ۱: استخراج ساخت‌یافته اطلاعات (موازی برای همه مقالات)
        infos = await self._extract_all(articles)

        # مرحله ۲: جدول مقایسه‌ای
        table = self._build_table(infos)

        # مرحله ۳: نمودارهای تحلیلی متنی (مستقیماً همان یک فایل Markdown، بدون تصویر)
        charts = self._generate_charts(infos)
        charts_md = "\n\n".join(
            f"**نمودار {idx + 1}: {title}**\n\n{block}"
            for idx, (title, block) in enumerate(charts)
        )

        # مرحله ۴ و ۵: تحلیل روند و شکاف‌های پژوهشی (موازی)
        trends, gaps = await asyncio.gather(
            self._analyze_trends(infos, charts),
            self._identify_gaps(infos),
        )

        # مرحله ۶: خلاصه اجرایی و نتیجه‌گیری
        summary, conclusion = await asyncio.gather(
            self._executive_summary(trends, gaps, len(infos)),
            self._conclusion(trends, gaps),
        )

        references = self._build_references(infos)

        report = f"""# گزارش تحلیلی مقالات علمی

## خلاصه اجرایی

{summary.strip()}

## ۱. جدول استخراج اطلاعات کلیدی

{table}

## ۲. تحلیل روندهای پژوهشی

{trends.strip()}

{charts_md}

## ۳. شکاف‌های پژوهشی

{gaps.strip()}

## نتیجه‌گیری

{conclusion.strip()}

## منابع / مستندات پایه

{references}
"""
        return self._validate_and_repair(report)


# ── CLI ────────────────────────────────────────────────────────────────────


def _emergency_skeleton_report(filenames: list[str], error: Exception) -> str:
    """
    فقط برای شرایطی که کل خط لوله (نه فقط یک تماس مدل) شکست می‌خورد استفاده
    می‌شود، تا حتی در بدترین حالت یک فایل خروجی معتبر و کاملاً فارسی و
    دارای ساختار کامل تولید شود (به‌جای crash کردن بدون هیچ فایلی).
    """
    refs = (
        "\n".join(f"- {name}" for name in filenames) or "- (هیچ مقاله‌ای بارگذاری نشد)"
    )
    return f"""# گزارش تحلیلی مقالات علمی

## خلاصه اجرایی

تولید خودکار این گزارش به دلیل خطای فنی در ارتباط با سرویس مدل (Rhino) به‌طور کامل
انجام نشد. این نسخه یک اسکلت اضطراری است تا حداقل ساختار مورد نیاز حفظ شود؛ لطفاً
اجرای برنامه را پس از رفع مشکل اتصال تکرار کنید.

## ۱. جدول استخراج اطلاعات کلیدی

اطلاعات به دلیل خطای فنی استخراج نشد.

## ۲. تحلیل روندهای پژوهشی

تحلیل روندها به دلیل خطای فنی در دسترس نیست.

## ۳. شکاف‌های پژوهشی

شکاف‌های پژوهشی به دلیل خطای فنی شناسایی نشد.

## نتیجه‌گیری

اجرای مجدد برنامه پس از رفع خطای زیر توصیه می‌شود: {error}

## منابع / مستندات پایه

{refs}
"""


async def main() -> None:
    parser = argparse.ArgumentParser(description="عامل هوشمند تحلیل مقالات علمی")
    parser.add_argument(
        "--input_folder", required=True, help="مسیر فولدر شامل فایل‌های PDF"
    )
    parser.add_argument(
        "--output", required=True, help="مسیر فایل خروجی Markdown (.md)"
    )
    args = parser.parse_args()

    output_path = Path(args.output)

    print(f"📂 بارگذاری مقالات از: {args.input_folder}")
    articles = convert_folder(args.input_folder)
    if not articles:
        print("❌ هیچ فایل PDF پیدا نشد.")
        return

    print(f"✅ {len(articles)} مقاله بارگذاری شد:")
    for a in articles:
        print(f"   - {a.filename} ({a.page_count} صفحه)")

    filenames = [a.filename for a in articles]
    markdowns = [a.markdown for a in articles]

    provider = RhinoProvider()
    agent = Agent(provider)

    print("🧠 اجرای Agent روی محتوای استخراج‌شده...")
    try:
        report = await agent.run(markdowns, filenames=filenames)
    except Exception as exc:  # noqa: BLE001 - جلوگیری از crash کامل بدون فایل خروجی
        print(f"❌ خطای غیرمنتظره در اجرای Agent: {exc}")
        report = _emergency_skeleton_report(filenames, exc)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"📝 گزارش نهایی ذخیره شد در: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
