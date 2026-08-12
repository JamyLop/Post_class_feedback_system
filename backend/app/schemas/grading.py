from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ConfirmGradingParams(BaseModel):
    """教师复核单题：可覆盖分数、补充评语。分数缺省沿用 AI 分数。"""

    teacher_score: float | None = None
    teacher_comment: str = ""


class FlagGradingParams(BaseModel):
    """标记异常：教师认为 AI 结果不可信，需记录原因。"""

    teacher_comment: str = ""


class ReviewSubmissionOut(BaseModel):
    submission_id: int
    assignment_id: int
    assignment_title: str
    student_id: int
    student_name: str
    content_type: str
    status: str
    total_score: float | None
    max_total: float
    answer_count: int
    confirmed_count: int
    review_state: str
    submitted_at: datetime


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