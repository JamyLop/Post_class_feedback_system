from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class FeedbackGenerateIn(BaseModel):
    report_type: Literal["assignment", "weekly"]
    class_id: int
    assignment_id: int | None = None
    period_start: date | None = None
    period_end: date | None = None


class FeedbackUpdateIn(BaseModel):
    final_content: str = Field(min_length=1, max_length=2000)


class FeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    class_id: int
    assignment_id: int | None
    report_type: str
    period_start: date | None
    period_end: date | None
    status: str
    input_snapshot: Any
    ai_content: str
    final_content: str
    model_name: str
    prompt_version: str
    total_tokens: int
    duration_ms: int
    error_message: str
    reviewed_by: int | None
    generated_at: datetime | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime
