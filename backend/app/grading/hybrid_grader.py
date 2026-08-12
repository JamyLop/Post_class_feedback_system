"""混合批改：填空题。规则优先，规则无法判定时交 LLM（实施计划第 8.1 节）。"""

from app.grading.base import BaseGrader, GradeResult
from app.grading.llm_grader import LLMGrader
from app.grading.rule_grader import normalize_text
from app.grading.schemas import GradeParams

_SEP = "；;，,、"


def _split_fill(s: str) -> list[str]:
    for ch in _SEP:
        s = s.replace(ch, "|")
    return [p.strip() for p in s.split("|") if p.strip()]


class HybridGrader(BaseGrader):
    grading_type = "hybrid"

    def __init__(self):
        self._llm = LLMGrader()

    def grade(self, params: GradeParams) -> GradeResult:
        answer = (params.student_answer or "").strip()
        if not answer:
            return GradeResult(
                score=0.0,
                max_score=params.max_score,
                is_correct=False,
                confidence=1.0,
                error_type="missing_answer",
                comment="未作答",
                grading_type=self.grading_type,
                model_name="rule",
            )

        # 规则优先：完整匹配（含多空一一对应）
        std = _split_fill(params.standard_answer)
        stu = _split_fill(answer)
        if std and len(std) == len(stu):
            matched = all(normalize_text(a) == normalize_text(b) for a, b in zip(std, stu))
            if matched:
                return GradeResult(
                    score=float(params.max_score),
                    max_score=params.max_score,
                    is_correct=True,
                    confidence=1.0,
                    error_type=None,
                    comment="回答正确",
                    grading_type=self.grading_type,
                    model_name="rule",
                )

        # 无法规则判定（部分对/术语差异）：交 LLM 评估部分分
        result = self._llm.grade(params)
        result.grading_type = self.grading_type
        return result