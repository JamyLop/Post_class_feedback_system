"""批改路由器：按题型分发到不同 Grader（实施计划第 8.1 节）。"""

from app.grading.base import GradeResult
from app.grading.hybrid_grader import HybridGrader
from app.grading.llm_grader import LLMGrader
from app.grading.rule_grader import RuleGrader
from app.grading.schemas import GradeParams

_RULE_TYPES = {"single_choice", "multiple_choice", "judge"}
_FILL_TYPES = {"fill"}


class GradingRouter:
    """按题型分发：客观题→规则，填空题→混合，主观题→LLM。"""

    def __init__(self):
        self._rule = RuleGrader()
        self._hybrid = HybridGrader()
        self._llm = LLMGrader()

    def grade(self, params: GradeParams) -> GradeResult:
        if params.question_type in _RULE_TYPES:
            return self._rule.grade(params)
        if params.question_type in _FILL_TYPES:
            return self._hybrid.grade(params)
        return self._llm.grade(params)


router = GradingRouter()
