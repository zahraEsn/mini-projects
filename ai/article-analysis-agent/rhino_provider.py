"""
rhino_provider.py — اتصال به مدل ما (Rhino)

⚠️ این فایل را تغییر ندهید — فقط از آن استفاده کنید.
⚠️ توکن، آدرس سرویس و نام مدل از فایل .env خوانده می‌شوند.
⚠️ هیچ وابستگی خاصی جز httpx ندارد.

استفاده در کلاس agent خودتان:

    from rhino_provider import RhinoProvider

    provider = RhinoProvider()

    response_text = await provider.complete([
        {"role": "system", "content": "تو یک دستیار تحلیل‌گر علمی هستی."},
        {"role": "user", "content": "این متن را خلاصه کن: ..."},
    ])
"""

from __future__ import annotations

import json
import os
from typing import AsyncIterator

import httpx

Message = dict[str, str]
# {"role": "system"|"user"|"assistant", "content": "..."}


def _messages_to_rhino(messages: list[Message]) -> list[dict]:
    """
    پیام‌های ساده را به فرمت Chat Completions تبدیل می‌کند.

    نقش‌های پشتیبانی‌شده:
    - system
    - user
    - assistant

    نقش نامعتبر به user تبدیل می‌شود.
    """
    result = []

    for message in messages:
        role = str(message.get("role", "user"))
        content = str(message.get("content", ""))

        if role not in {"system", "user", "assistant"}:
            role = "user"

        result.append(
            {
                "role": role,
                "content": content,
            }
        )

    return result


class RhinoProvider:
    """
    اتصال ساده به مدل Rhino — برای این چالش فقط متد complete() لازم است.

    تنظیمات لازم در فایل .env:

        RHINO_CHAT_URL=https://exam.mabnai.ir/llm/v1/chat/completions
        RHINO_API_KEY=...
        RHINO_MODEL=CoreStableLLM

    برای سازگاری، نام مدل از LLM_MODEL نیز خوانده می‌شود.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        profile: dict | None = None,
    ) -> None:
        self._url = base_url or os.environ["RHINO_CHAT_URL"]
        self._api_key = api_key or os.environ["RHINO_API_KEY"]

        self._model = (
            os.getenv("RHINO_MODEL") or os.getenv("LLM_MODEL") or "CoreStableLLM"
        )

        # برای حفظ سازگاری با کد اولیه نگه داشته شده است.
        self._profile = profile or {}

    def _build_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "Connection": "keep-alive",
        }

    def _build_payload(self, messages: list[Message]) -> dict:
        return {
            "model": self._model,
            "messages": _messages_to_rhino(messages),
            "stream": True,
        }

    async def complete(
        self,
        messages: list[Message],
        **kwargs,
    ) -> str:
        """
        پاسخ کامل مدل را برمی‌گرداند.

        پاسخ در سطح API به‌صورت Stream دریافت می‌شود، اما این متد
        همه Chunkها را به هم متصل کرده و متن کامل را برمی‌گرداند.

        Parameters:
            messages:
                لیستی از دیکشنری‌های پیام، مثلاً:

                [
                    {"role": "system", "content": "..."},
                    {"role": "user", "content": "..."},
                ]

        Returns:
            متن کامل پاسخ مدل.
        """
        full_text = ""

        async for chunk in self._stream(messages):
            full_text += chunk

        return full_text

    async def _stream(
        self,
        messages: list[Message],
    ) -> AsyncIterator[str]:
        """
        پاسخ SSE را دریافت می‌کند و فقط محتوای نهایی مدل را yield می‌کند.

        Chunkهای reasoning عمداً وارد خروجی نهایی نمی‌شوند.
        """
        payload = self._build_payload(messages)
        headers = self._build_headers()

        async with httpx.AsyncClient(
            timeout=120,
            follow_redirects=True,
        ) as client:
            async with client.stream(
                "POST",
                self._url,
                json=payload,
                headers=headers,
            ) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    error_text = error_body.decode(
                        "utf-8",
                        errors="replace",
                    )

                    raise RuntimeError(
                        f"خطای سرویس Rhino "
                        f"(کد {response.status_code}): "
                        f"{error_text or 'بدون توضیح'}"
                    )

                async for raw_line in response.aiter_lines():
                    if not raw_line:
                        continue

                    if not raw_line.startswith("data:"):
                        continue

                    text_line = raw_line[5:].strip()

                    if not text_line:
                        continue

                    if text_line == "[DONE]":
                        break

                    try:
                        data: dict = json.loads(text_line)
                    except json.JSONDecodeError:
                        continue

                    choices = data.get("choices") or []

                    # Chunk نهایی usage ممکن است choices خالی داشته باشد.
                    if not choices:
                        continue

                    choice = choices[0]
                    delta = choice.get("delta") or {}

                    # فقط پاسخ نهایی مدل خوانده می‌شود؛
                    # delta.reasoning وارد خروجی نمی‌شود.
                    text = delta.get("content") or ""

                    if text:
                        yield str(text)

                    # سرویس فعلی الزاماً data: [DONE] نمی‌فرستد
                    # و پایان پاسخ را با finish_reason مشخص می‌کند.
                    if choice.get("finish_reason") is not None:
                        break
