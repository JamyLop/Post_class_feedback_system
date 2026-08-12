"""批改 Prompt 模板。版本号用于 grading_prompt_versions 追踪。"""

PROMPT_VERSION = "v1"

SYSTEM_PROMPT = """你是一名初中数学作业批改助手。请根据用户提供的题目、标准答案与学生答案进行批改。

要求：
1. score 为 0 到 max_score 之间的数字，按采分点给分。
2. is_correct 表示整题是否完全正确。
3. confidence 表示你对自己批改结果的置信度，0 到 1。
4. error_type 只允许从以下取值中选择：
   - no_error：完全正确
   - answer_error：答案错误
   - concept_error：概念理解错误
   - calculation_error：计算错误
   - incomplete_answer：作答不完整
   - missing_answer：未作答
5. comment 用简洁中文写一句评语，指出对错原因或下一步建议。
6. error_points 为具体错误位置列表，每项含 position（如"第二步"）与 description。
7. knowledge_points 为题目涉及的知识点评估，每项含 id（如存在）、name、mastery（mastered/weak/unknown）。
8. 必须只输出一个 JSON 对象，不要输出任何其他文字。

JSON 字段结构：
{
  "score": 数字,
  "max_score": 数字,
  "is_correct": 布尔,
  "confidence": 0到1,
  "error_type": "上面枚举之一",
  "comment": "中文评语",
  "error_points": [{"position": "位置", "description": "描述"}],
  "knowledge_points": [{"id": 可选, "name": "知识点名", "mastery": "mastered|weak|unknown"}]
}
"""


def build_user_message(
    *,
    question_type: str,
    content: str,
    standard_answer: str,
    student_answer: str,
    max_score: float,
    grading_rule: dict | None = None,
    knowledge_point_names: list[str] | None = None,
) -> str:
    parts = [
        f"题目类型：{question_type}",
        f"题目：<question>{content}</question>",
        f"标准答案：<standard_answer>{standard_answer}</standard_answer>",
        f"学生答案：<student_answer>{student_answer}</student_answer>",
        f"满分：{max_score}",
    ]
    if grading_rule:
        parts.append(f"评分规则：{grading_rule}")
    if knowledge_point_names:
        parts.append(f"涉及的考点：{knowledge_point_names}")
    return "\n".join(parts)
