from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class WeeklyTestScoreCreate(BaseModel):
    class_id: int
    student_id: int
    subject: str = Field(min_length=1, max_length=32)
    exam_date: date
    exam_name: str = Field(default="", max_length=64)
    score: float = Field(ge=0)
    max_score: float = Field(default=100, gt=0, le=1000)
    rank_in_class: int | None = Field(default=None, ge=1)
    remark: str = Field(default="", max_length=500)


class WeeklyTestScoreUpdate(BaseModel):
    subject: str | None = Field(default=None, min_length=1, max_length=32)
    exam_date: date | None = None
    exam_name: str | None = Field(default=None, max_length=64)
    score: float | None = Field(default=None, ge=0)
    max_score: float | None = Field(default=None, gt=0, le=1000)
    rank_in_class: int | None = Field(default=None, ge=1)
    remark: str | None = Field(default=None, max_length=500)


class WeeklyTestScoreBatchCreate(BaseModel):
    class_id: int
    subject: str = Field(min_length=1, max_length=32)
    exam_date: date
    exam_name: str = Field(default="", max_length=64)
    max_score: float = Field(default=100, gt=0, le=1000)
    records: list[dict] = Field(description="每条含 student_id, score, rank_in_class, remark")


class WeeklyTestScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    class_id: int
    student_id: int
    subject: str
    exam_date: date
    exam_name: str
    score: float
    max_score: float
    rank_in_class: int | None
    remark: str
    recorded_by: int
    created_at: datetime
    updated_at: datetime
    student_name: str | None = None
    class_name: str | None = None


class WeeklyTestTrendPoint(BaseModel):
    exam_date: date
    exam_name: str
    score: float
    max_score: float


class ClassWeeklySummary(BaseModel):
    exam_date: date
    exam_name: str
    subject: str
    avg_score: float
    max_score: float
    min_score: float
    count: int
