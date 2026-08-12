from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class GradingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    submission_answer_id: int
    grading_type: str
    model_name: str
    ai_score: float | None
    ai_comment: str
    confidence: float
    error_type: str | None
    error_points: Any = None
    knowledge_points: Any = None
    prompt_version: str
    teacher_score: float | None
    teacher_comment: str
    status: str
    reviewed_at: datetime | None


class SubmissionAnswerGradingOut(BaseModel):
    answer_id: int
    question_order: int
    question_type: str
    content: str
    standard_answer: str
    student_answer: str
    ocr_text: str
    score: float | None
    max_score: float | None
    is_correct: bool | None
    grading: GradingOut | None = None


class SubmissionGradingOut(BaseModel):
    submission_id: int
    status: str
    total_score: float | None
    max_total: float
    answers: list[SubmissionAnswerGradingOut] = []