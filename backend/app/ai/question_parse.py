"""题目解析：将 OCR/文本内容解析为结构化题目列表（AI 辅助建题）。"""

import json
import logging
import re
from typing import Any

from app.ai.provider import get_llm_provider

logger = logging.getLogger(__name__)

PROMPT_VERSION = "v1"

SYSTEM_PROMPT = """你是一名初中数学命题助手。请将用户提供的题目文本解析为结构化的题目列表。

要求：
1. 识别每道题的题型，只允许使用：single_choice、multiple_choice、judge、fill、calculation、short_answer。
2. 提取题干 content、标准答案 standard_answer、分值 score、难度 difficulty（0~1）。
3. 一道题只能有一个 question_type。
4. 只输出 JSON 数组，不要输出任何其他文字。格式：
[
  {
    "question_type": "calculation",
    "content": "题干",
    "standard_answer": "标准答案",
    "score": 10,
    "difficulty": 0.6
  }
]
"""

_PARSE_TAG = re.compile(r"<question_parse>(.*?)</question_parse>", re.S)


def _extract_json_array(text: str) -> str:
    """从 LLM 输出中截取 JSON 数组片段（容忍代码块包裹）。"""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("输出中未找到 JSON 数组")
    return text[start : end + 1]


def parse_questions(raw_text: str) -> list[dict[str, Any]]:
    """调用 LLM 将文本解析为题目列表，失败时抛出 ValueError。"""
    if not (raw_text or "").strip():
        raise ValueError("没有可解析的内容")
    provider = get_llm_provider()
    user = f"<question_parse>{raw_text.strip()}</question_parse>"
    raw = provider.chat(SYSTEM_PROMPT, user, response_format="json")
    try:
        arr = json.loads(_extract_json_array(raw))
    except (ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"题目解析 JSON 解析失败: {exc}") from exc
    if not isinstance(arr, list):
        raise ValueError("题目解析输出不是数组")
    questions = []
    # 过滤掉缺题干或结构非法的条目
    for item in arr:
        if not isinstance(item, dict) or not item.get("content"):
            continue
        questions.append(item)
    if not questions:
        raise ValueError("未解析出有效题目")
    return questions