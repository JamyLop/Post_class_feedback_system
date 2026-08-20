"""LLM 提供方抽象：mock 启发式实现 + OpenAI 兼容接口实现。

统一封装 LLM 调用，附带 token/耗时元数据；支持 mock 模式离线打通全链路。
"""

from __future__ import annotations

import json
import logging
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

# 用于从批改 prompt 中提取题目/答案标签与满分
_TAG = re.compile(r"<(question|standard_answer|student_answer)>(.*?)</\1>", re.S)
_SCORE = re.compile(r"满分[:：]\s*([0-9.]+)")


@dataclass
class LLMResponse:
    """LLM 一次调用的输出：文本 + 模型 + 用量元数据。"""

    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    duration_ms: int = 0


class LLMProvider(ABC):
    @abstractmethod
    def chat_with_metadata(
        self,
        system: str,
        user: str,
        response_format: str = "text",
    ) -> LLMResponse:
        ...

    def chat(self, system: str, user: str, response_format: str = "text") -> str:
        """便捷方法：只返回文本。"""
        return self.chat_with_metadata(system, user, response_format).text


def _normalize(s: str) -> str:
    """去空白、小写，用于字符相似度比较。"""
    return re.sub(r"\s+", "", s or "").lower()


class MockLLMProvider(LLMProvider):
    """开发期替身：基于题目/标准答案/学生答案的字符相似度给出启发式评分，
    返回与真实 LLM 一致的结构化 JSON，便于打通全链路并演示置信度策略。"""

    def chat_with_metadata(
        self, system: str, user: str, response_format: str = "text"
    ) -> LLMResponse:
        if "<feedback_data>" in user:
            return LLMResponse(
                text=(
                    "本阶段作业已完成，整体表现较为稳定。建议优先复习掌握度较低的知识点，"
                    "结合错题重新梳理解题步骤；对重复出现的错误进行归类，每天安排少量针对性练习，"
                    "完成后及时核对过程与结论。"
                ),
                model="mock-feedback",
            )
        if "<question_parse>" in user:
            return LLMResponse(
                text=json.dumps(self._parse_questions(user), ensure_ascii=False),
                model="mock-parser",
            )
        tags = {m.group(1): m.group(2).strip() for m in _TAG.finditer(user)}
        max_score = float(_SCORE.search(user).group(1)) if _SCORE.search(user) else 10.0
        student = tags.get("student_answer", "").strip()
        standard = tags.get("standard_answer", "").strip()
        return LLMResponse(
            text=json.dumps(
                self._heuristic(student, standard, max_score), ensure_ascii=False
            ),
            model="mock-grader",
        )

    @staticmethod
    def _parse_questions(user: str) -> list[dict]:
        """开发期替身：按空行切分为多道题，逐题生成结构化结果。"""
        match = re.search(r"<question_parse>(.*?)</question_parse>", user, re.S)
        raw = match.group(1) if match else user
        blocks = [b.strip() for b in raw.split("\n\n") if b.strip()]
        if not blocks:
            return []
        return [
            {
                "question_type": "calculation",
                "content": block,
                "standard_answer": "",
                "score": 10.0,
                "difficulty": 0.5,
            }
            for block in blocks
        ]

    def _heuristic(self, student: str, standard: str, max_score: float) -> dict:
        """按相似度打分：>=0.95 全对、>=0.7 不完整、其余视为答案错误。"""
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
    """真实 LLM 提供方：OpenAI 兼容 Chat Completions 接口。"""

    def __init__(self):
        self.client = OpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )

    def chat_with_metadata(
        self, system: str, user: str, response_format: str = "text"
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": settings.llm_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        # json 模式要求模型输出合法 JSON 对象
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}
        started = time.perf_counter()
        try:
            resp = self.client.chat.completions.create(**kwargs)
        except Exception:
            logger.exception(
                "llm_call_failed provider=openai_compat model=%s", settings.llm_model
            )
            raise
        duration_ms = round((time.perf_counter() - started) * 1000)
        usage = resp.usage
        result = LLMResponse(
            text=resp.choices[0].message.content or "",
            model=resp.model or settings.llm_model,
            prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
            total_tokens=getattr(usage, "total_tokens", 0) or 0,
            duration_ms=duration_ms,
        )
        logger.info(
            "llm_call_succeeded model=%s duration_ms=%s prompt_tokens=%s completion_tokens=%s total_tokens=%s",
            result.model,
            result.duration_ms,
            result.prompt_tokens,
            result.completion_tokens,
            result.total_tokens,
        )
        return result


_provider: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    """按配置懒加载 LLM 提供方（单例）。"""
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
