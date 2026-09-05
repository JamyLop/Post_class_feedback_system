"""AI 输出解析与结构化校验（实施计划第 10 节）。"""

import json
import re
from typing import Any

from app.ai.provider import get_llm_provider
from app.core.config import settings
from app.grading.schemas import AIGrading

PARSE_MAX_RETRIES = 1


def _extract_json_object(text: str) -> str:
    """从 LLM 输出中截取 JSON 对象片段（容忍代码块包裹与前后文字）。"""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("输出中未找到 JSON 对象")
    return text[start : end + 1]


def parse_and_validate(raw_text: str) -> AIGrading:
    """解析 LLM 原始文本并做 Pydantic 校验，失败时抛出 ValueError。"""
    try:
        obj: dict[str, Any] = json.loads(_extract_json_object(raw_text))
    except (ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"AI JSON 解析失败: {exc}") from exc
    grading = AIGrading.model_validate(obj)
    _clamp(grading)
    return grading


def _clamp(grading: AIGrading) -> None:
    """约束分数与置信度取值范围，避免模型越界输出。"""
    if grading.score is not None and grading.max_score is not None:
        grading.score = max(0.0, min(float(grading.max_score), float(grading.score)))
    grading.confidence = max(0.0, min(1.0, float(grading.confidence)))


def request_grading(
    *,
    system: str,
    user: str,
    model_name: str,
) -> tuple[AIGrading, str]:
    """调用 LLM 并校验结构化输出。

    返回 (grading, raw_text)。校验失败重试一次；仍失败则抛出 ValueError，
    由上层降级为人工复核（status=manual_review）。
    """
    provider = get_llm_provider()
    raw = provider.chat(system, user, response_format="json")
    last_error: Exception | None = None
    for _ in range(PARSE_MAX_RETRIES + 1):
        try:
            return parse_and_validate(raw), raw
        except ValueError as exc:
            last_error = exc
            raw = provider.chat(system, user, response_format="json")
    raise ValueError(f"AI 结构化输出校验失败：{last_error}") from last_error


def default_model_name() -> str:
    return settings.llm_model if settings.llm_provider != "mock" else "mock-heuristic"
