from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AssignmentCreate(BaseModel):
    class_id: int
    title: str = Field(min_length=1, max_length=128)
    subject: str = Field(min_length=1, max_length=32)
    description: str = Field(default="", max_length=512)
    due_at: datetime | None = None


class AssignmentUpdate(BaseModel):
    title: str | None = None
    subject: str | None = None
    description: str | None = None
    due_at: datetime | None = None
    status: Literal["draft", "published", "closed", "archived"] | None = None


class AssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    class_id: int
    teacher_id: int
    title: str
    subject: str
    description: str
    due_at: datetime | None
    status: str


class AssignmentQuestionRef(BaseModel):
    question_id: int
    question_order: int = 0


class AssignmentAddQuestions(BaseModel):
    question_ids: list[int] = Field(min_length=1)


class AssignmentQuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_order: int
    question_type: str
    content: str
    score: float
    # 学生接口返回 None，避免在作答前泄露标准答案。
    standard_answer: str | None = None


class AssignmentDetail(AssignmentOut):
    questions: list[AssignmentQuestionOut] = []
