from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from openai import OpenAI

from app.core.config import settings


class LLMProvider(ABC):
    @abstractmethod
    def chat(
        self,
        system: str,
        user: str,
        response_format: str = "text",
    ) -> str:
        ...


class MockLLMProvider(LLMProvider):
    """开发期替身：返回结构化占位 JSON，便于打通全链路。"""

    def chat(self, system: str, user: str, response_format: str = "text") -> str:
        return json.dumps(
            {
                "score": None,
                "max_score": None,
                "is_correct": None,
                "confidence": 0.0,
                "error_type": None,
                "comment": "[MockLLM] 请配置真实 LLM 后重新批改",
                "error_points": [],
                "knowledge_points": [],
            },
            ensure_ascii=False,
        )


class OpenAICompatProvider(LLMProvider):
    def __init__(self):
        self.client = OpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )

    def chat(self, system: str, user: str, response_format: str = "text") -> str:
        kwargs: dict[str, Any] = {
            "model": settings.llm_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}
        resp = self.client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""


_provider: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    global _provider
    if _provider is None:
        if settings.llm_provider == "mock":
            _provider = MockLLMProvider()
        elif settings.llm_provider == "openai_compat":
            _provider = OpenAICompatProvider()
        else:
            raise NotImplementedError(
                f"LLM provider '{settings.llm_provider}' 不支持"
            )
    return _provider
