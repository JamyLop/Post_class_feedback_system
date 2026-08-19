from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.question import QUESTION_TYPES


class KnowledgePointRef(BaseModel):
    id: int
    weight: float = 1.0


class QuestionCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=32)
    grade: str = Field(min_length=1, max_length=32)
    question_type: str = Field(pattern=f"^({'|'.join(QUESTION_TYPES)})$")
    content: str = Field(min_length=1, max_length=2000)
    standard_answer: str = Field(default="", max_length=2000)
    score: float = Field(default=0, ge=0)
    difficulty: float = Field(default=0.5, ge=0, le=1)
    grading_rule: Any = None
    knowledge_points: list[KnowledgePointRef] = []


class QuestionUpdate(BaseModel):
    content: str | None = None
    standard_answer: str | None = None
    score: float | None = Field(default=None, ge=0)
    difficulty: float | None = Field(default=None, ge=0, le=1)
    grading_rule: Any = None


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject: str
    grade: str
    question_type: str
    content: str
    standard_answer: str
    score: float
    difficulty: float
    grading_rule: Any = None


class QuestionDetail(QuestionOut):
    knowledge_points: list[dict] = []

    model_config = ConfigDict(from_attributes=True)


class QuestionParseOut(BaseModel):
    """AI 解析出的题目预览（尚未入库，入库需再调 /questions/batch）。"""

    question_type: str
    content: str = Field(max_length=2000)
    standard_answer: str = Field(default="", max_length=2000)
    score: float = Field(default=0, ge=0)
    difficulty: float = Field(default=0.5, ge=0, le=1)


class QuestionBatchCreate(BaseModel):
    questions: list[QuestionCreate] = Field(min_length=1)
