"""规则批改：选择题（单选/多选）与判断题。

客观题不调用 LLM，直接按标准答案比对（实施计划第 24 节成本控制）。
"""

import re

from app.grading.base import BaseGrader, GradeResult
from app.grading.schemas import GradeParams

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[。，,、．.；;：:\s]+")


def normalize_text(s: str) -> str:
    return _PUNCT.sub("", s).lower()


def extract_choices(s: str) -> str:
    """从答案文本中提取大写选项字母，如 'AB'。"""
    found = "".join(re.findall(r"[A-Ea-e]", s)).upper()
    # 去重但保持顺序
    return "".join(dict.fromkeys(found))


def normalize_judge(s: str) -> bool | None:
    t = normalize_text(s)
    if not t:
        return None
    if t in {"对", "正确", "√", "✓", "v", "true", "t", "是", "1", "yes", "right", "ok"}:
        return True
    if t in {"错", "错误", "×", "✗", "x", "false", "f", "否", "0", "no", "wrong"}:
        return False
    return None


class RuleGrader(BaseGrader):
    grading_type = "rule"

    def grade(self, params: GradeParams) -> GradeResult:
        max_score = params.max_score or 0
        answer = (params.student_answer or "").strip()

        if not answer:
            return self._finish(
                params,
                is_correct=False,
                score=0.0,
                confidence=1.0,
                error_type="missing_answer",
                comment="未作答",
            )

        if params.question_type == "judge":
            ok, wrong_type, comment = self._grade_judge(params)
        else:
            ok, wrong_type, comment = self._grade_choice(params)

        if ok is None:
            # 答案无法解析（如学生写了文字而非选项字母），交给人工复核
            return self._finish(
                params,
                is_correct=None,
                score=None,
                confidence=0.5,
                error_type="answer_error",
                comment="答案格式无法识别，请人工复核",
            )
        if ok:
            return self._finish(
                params,
                is_correct=True,
                score=float(max_score),
                confidence=1.0,
                error_type=None,
                comment="回答正确",
            )
        return self._finish(
            params,
            is_correct=False,
            score=0.0,
            confidence=1.0,
            error_type=wrong_type,
            comment=comment,
        )

    def _grade_choice(self, params: GradeParams) -> tuple[bool | None, str, str]:
        std = extract_choices(params.standard_answer)
        stu = extract_choices(params.student_answer)
        if not std or not stu:
            return None, "answer_error", "答案格式无法识别，请人工复核"
        if params.question_type == "multiple_choice":
            ok = set(std) == set(stu)
        else:
            ok = std == stu
        if ok:
            return True, "", ""
        return False, "answer_error", "选项与标准答案不符"

    def _grade_judge(self, params: GradeParams) -> tuple[bool | None, str, str]:
        std = normalize_judge(params.standard_answer)
        stu = normalize_judge(params.student_answer)
        if std is None or stu is None:
            return None, "answer_error", "答案格式无法识别，请人工复核"
        return std == stu, "answer_error", "判断结果与标准答案不符"

    def _finish(
        self,
        params: GradeParams,
        *,
        is_correct: bool | None,
        score: float | None,
        confidence: float,
        error_type: str | None,
        comment: str,
    ) -> GradeResult:
        return GradeResult(
            score=score,
            max_score=params.max_score,
            is_correct=is_correct,
            confidence=confidence,
            error_type=error_type,
            comment=comment,
            grading_type=self.grading_type,
            model_name="rule",
        )
