from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from difflib import SequenceMatcher
from typing import Any

from openai import OpenAI

from app.core.config import settings

_TAG = re.compile(r"<(question|standard_answer|student_answer)>(.*?)</\1>", re.S)
_SCORE = re.compile(r"满分[:：]\s*([0-9.]+)")


class LLMProvider(ABC):
    @abstractmethod
    def chat(
        self,
        system: str,
        user: str,
        response_format: str = "text",
    ) -> str:
        ...


def _normalize(s: str) -> str:
    return re.sub(r"\s+", "", s or "").lower()


class MockLLMProvider(LLMProvider):
    """开发期替身：基于题目/标准答案/学生答案的字符相似度给出启发式评分，
    返回与真实 LLM 一致的结构化 JSON，便于打通全链路并演示置信度策略。"""

    def chat(self, system: str, user: str, response_format: str = "text") -> str:
        tags = {m.group(1): m.group(2).strip() for m in _TAG.finditer(user)}
        max_score = float(_SCORE.search(user).group(1)) if _SCORE.search(user) else 10.0
        student = tags.get("student_answer", "").strip()
        standard = tags.get("standard_answer", "").strip()
        return json.dumps(
            self._heuristic(student, standard, max_score),
            ensure_ascii=False,
        )

    def _heuristic(self, student: str, standard: str, max_score: float) -> dict:
        if not student:
            return {
                "score": 0,
                "max_score": max_score,
                "is_correct": False,
                "confidence": 1.0,
                "error_type": "missing_answer",
                "comment": "未作答",
                "error_points": [],
                "knowledge_points": [],
            }
        ratio = SequenceMatcher(None, _normalize(standard), _normalize(student)).ratio()
        if ratio >= 0.95:
            return {
                "score": max_score,
                "max_score": max_score,
                "is_correct": True,
                "confidence": 0.92,
                "error_type": "no_error",
                "comment": "答案与标准答案基本一致，回答正确。",
                "error_points": [],
                "knowledge_points": [],
            }
        if ratio >= 0.7:
            return {
                "score": round(max_score * ratio, 1),
                "max_score": max_score,
                "is_correct": False,
                "confidence": 0.78,
                "error_type": "incomplete_answer",
                "comment": "作答不完整或与标准答案有偏差，建议核对步骤与结论。",
                "error_points": [],
                "knowledge_points": [],
            }
        return {
            "score": round(max_score * ratio, 1),
            "max_score": max_score,
            "is_correct": False,
            "confidence": 0.6,
            "error_type": "answer_error",
            "comment": "答案与标准答案差异较大，请结合标准答案复核。",
            "error_points": [],
            "knowledge_points": [],
        }


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
