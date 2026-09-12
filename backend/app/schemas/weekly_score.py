from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WeeklyScoreEvaluationSave(BaseModel):
    # 评价人由登录身份和班级任课关系确定，拒绝客户端指定评价人。
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content", mode="before")
    @classmethod
    def strip_content(cls, value):
        return value.strip() if isinstance(value, str) else value


class WeeklyScoreEvaluationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    teacher_id: int
    teacher_name: str
    teacher_role: str
    content: str
    created_at: datetime
    updated_at: datetime


class WeeklyTestScoreCreate(BaseModel):
    class_id: int
    student_id: int
    subject: str = Field(min_length=1, max_length=32)
    exam_date: date
    exam_name: str = Field(default="", max_length=64)
    score: float = Field(ge=0)
    max_score: float = Field(gt=0, le=1000)
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
    max_score: float = Field(gt=0, le=1000)
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
    evaluations: list[WeeklyScoreEvaluationOut] = Field(default_factory=list)
    can_evaluate: bool = False


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
