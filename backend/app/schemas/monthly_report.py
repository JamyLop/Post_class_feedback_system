from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MonthlyReportScopeIn(BaseModel):
    student_id: int
    class_id: int
    month_label: str = Field(pattern=r"^\d{4}-\d{2}$", description="YYYY-MM")
    student_case_id: int | None = None


class MonthlyReportUpdateIn(BaseModel):
    final_content: str = Field(min_length=1, max_length=8000)

    @field_validator("final_content")
    @classmethod
    def require_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("请填写评定内容")
        return value


class MonthlyReportCreateIn(MonthlyReportScopeIn, MonthlyReportUpdateIn):
    pass


class MonthlyEvaluationSave(BaseModel):
    # 评价人由登录身份和班级任课关系确定，拒绝客户端指定评价人。
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content", mode="before")
    @classmethod
    def strip_content(cls, value):
        return value.strip() if isinstance(value, str) else value


class MonthlyEvaluationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    teacher_id: int
    teacher_name: str
    teacher_role: str
    subject: str = ""
    content: str
    created_at: datetime
    updated_at: datetime


class MonthlyReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    class_id: int
    student_case_id: int | None
    month_label: str
    period_start: date
    period_end: date
    status: str
    input_snapshot: Any
    ai_content: str
    final_content: str
    model_name: str
    prompt_version: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    duration_ms: int
    error_message: str
    reviewed_by: int | None
    generated_at: datetime | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime
    student_name: str | None = None
    class_name: str | None = None
    evaluations: list[MonthlyEvaluationOut] = Field(default_factory=list)
    can_evaluate: bool = False
