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
