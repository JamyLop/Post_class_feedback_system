"""LLM 批改：计算题、简答题。（实施计划第 8.1 节）"""

import logging

from app.grading import prompts
from app.grading.base import BaseGrader, GradeResult
from app.grading.schemas import GradeParams
from app.grading.validator import default_model_name, request_grading

logger = logging.getLogger(__name__)


class LLMGrader(BaseGrader):
    grading_type = "ai"

    def grade(self, params: GradeParams) -> GradeResult:
        max_score = params.max_score or 0
        if not (params.student_answer or "").strip():
            return GradeResult(
                score=0.0,
                max_score=max_score,
                is_correct=False,
                confidence=1.0,
                error_type="missing_answer",
                comment="未作答",
                grading_type=self.grading_type,
                model_name=default_model_name(),
            )

        user = prompts.build_user_message(
            question_type=params.question_type,
            content=params.content,
            standard_answer=params.standard_answer,
            student_answer=params.student_answer,
            max_score=max_score,
            grading_rule=params.grading_rule,
            knowledge_point_names=params.knowledge_point_names,
        )
        try:
            grading, raw = request_grading(
                system=prompts.SYSTEM_PROMPT,
                user=user,
                model_name=default_model_name(),
            )
        except ValueError as exc:
            logger.warning("LLM 批改结构化输出失败，降级人工复核: %s", exc)
            return GradeResult(
                score=None,
                max_score=max_score,
                is_correct=None,
                confidence=0.0,
                error_type="parse_failed",
                comment="AI 批改输出异常，请人工复核",
                grading_type=self.grading_type,
                model_name=default_model_name(),
                prompt_version=prompts.PROMPT_VERSION,
            )

        return GradeResult(
            score=grading.score,
            max_score=max_score,
            is_correct=grading.is_correct,
            confidence=grading.confidence,
            error_type=grading.error_type or None,
            comment=grading.comment or "",
            error_points=[ep.model_dump() for ep in grading.error_points],
            knowledge_points=[kp.model_dump() for kp in grading.knowledge_points],
            grading_type=self.grading_type,
            model_name=default_model_name(),
            raw_ai_result=grading.model_dump(),
            prompt_version=prompts.PROMPT_VERSION,
        )