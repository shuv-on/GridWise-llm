"""OpenAI-compatible LLM client (works with OpenAI, Groq, Gemini-compat)."""
import json
from typing import Any

import httpx
from openai import AsyncOpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings
from app.core.exceptions import LLMError, LLMRateLimited
from app.core.logging import get_logger
from app.services.llm.base import LLMClient
from app.services.llm.prompts import SYSTEM_PROMPT, build_user_prompt

log = get_logger("llm")


class OpenAICompatibleClient(LLMClient):
    """Async client for any OpenAI-compatible chat completion API."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.llm_api_key:
            raise LLMError("LLM_API_KEY is not set")
        self._settings = settings
        self._client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            timeout=settings.llm_timeout_seconds,
        )

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=3),
        reraise=True,
    )
    async def _call(self, messages: list[dict[str, str]]) -> str:
        try:
            response = await self._client.chat.completions.create(
                model=self._settings.llm_model,
                messages=messages,
                temperature=self._settings.llm_temperature,
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content or ""

        except Exception as exc:
            # --- Rate limit detection ---
            status_code = getattr(exc, "status_code", None)
            if status_code is None and hasattr(exc, "response"):
                status_code = getattr(exc.response, "status_code", None)

            if status_code == 429:
                log.warning("llm_rate_limited", provider=self._settings.llm_provider)
                raise LLMRateLimited(
                    "LLM provider rate limit hit"
                ) from exc

            log.warning("llm_call_failed", error=str(exc), status=status_code)
            raise

    async def interpret_notes(
        self,
        operator_notes: list[str],
        battery_capacity_kwh: float,
    ) -> list[dict]:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": build_user_prompt(operator_notes, battery_capacity_kwh),
            },
        ]

        raw = await self._call(messages)
        log.info("llm_raw_response", length=len(raw))

        try:
            parsed: Any = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMError(f"LLM did not return valid JSON: {exc}") from exc

        directives = parsed.get("directives")
        if not isinstance(directives, list):
            raise LLMError("LLM response missing 'directives' list")

        if len(directives) != len(operator_notes):
            raise LLMError(
                f"LLM returned {len(directives)} directives, "
                f"expected {len(operator_notes)}"
            )

        return directives


def get_llm_client() -> LLMClient:
    """Factory. Swap provider here if needed."""
    return OpenAICompatibleClient()