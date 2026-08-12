from pydantic import BaseModel, Field


class ErrorPointIn(BaseModel):
    position: str = ""
    description: str = ""


class KnowledgePointGrading(BaseModel):
    id: int | str | None = None
    name: str = ""
    mastery: str = "unknown"


class AIGrading(BaseModel):
    """AI 批改结构化输出（实施计划第 10 节 Schema）。"""

    score: float | None = None
    max_score: float | None = None
    is_correct: bool | None = None
    confidence: float = Field(default=0.0, ge=0, le=1)
    error_type: str | None = None
    comment: str = ""
    error_points: list[ErrorPointIn] = []
    knowledge_points: list[KnowledgePointGrading] = []


class GradeParams(BaseModel):
    """GradingRouter 内部入参。"""

    question_type: str
    content: str
    standard_answer: str
    student_answer: str
    max_score: float
    grading_rule: dict | None = None
    knowledge_point_names: list[str] = []
