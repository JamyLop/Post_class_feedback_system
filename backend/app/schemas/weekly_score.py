from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
    model_config = ConfigDict(allow_inf_nan=False)
    class_id: int
    student_id: int
    subject: str = Field(min_length=1, max_length=32)
    exam_date: date
    exam_month: str = Field(default="", pattern=r"^(?:[0-9]{4}-(?:0[1-9]|1[0-2]))?$")
    exam_name: str = Field(default="", max_length=64)
    score: float = Field(ge=0)
    max_score: float = Field(gt=0, le=1000)
    rank_in_class: int | None = Field(default=None, ge=1)
    remark: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def monthly_defaults(self):
        if not self.exam_month:
            self.exam_month = self.exam_date.strftime("%Y-%m")
        if not self.exam_name.strip():
            self.exam_name = f"{self.exam_month}月考"
        return self


class WeeklyTestScoreUpdate(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    subject: str | None = Field(default=None, min_length=1, max_length=32)
    exam_date: date | None = None
    exam_month: str | None = Field(default=None, pattern=r"^[0-9]{4}-(?:0[1-9]|1[0-2])$")
    exam_name: str | None = Field(default=None, max_length=64)
    score: float | None = Field(default=None, ge=0)
    max_score: float | None = Field(default=None, gt=0, le=1000)
    rank_in_class: int | None = Field(default=None, ge=1)
    remark: str | None = Field(default=None, max_length=500)


class MonthlyScoreRecord(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    student_id: int = Field(gt=0)
    score: float = Field(ge=0)
    max_score: float | None = Field(default=None, gt=0, le=1000)
    rank_in_class: int | None = Field(default=None, ge=1)
    remark: str = Field(default="", max_length=500)


class WeeklyTestScoreBatchCreate(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    class_id: int
    subject: str = Field(min_length=1, max_length=32)
    exam_date: date
    exam_month: str = Field(default="", pattern=r"^(?:[0-9]{4}-(?:0[1-9]|1[0-2]))?$")
    exam_name: str = Field(default="", max_length=64)
    max_score: float = Field(gt=0, le=1000)
    records: list[dict] = Field(min_length=1, description="每条含 student_id, score, rank_in_class, remark")

    @field_validator("records")
    @classmethod
    def validate_records(cls, records):
        validated = [MonthlyScoreRecord.model_validate(item).model_dump(exclude_none=True) for item in records]
        ids = [item["student_id"] for item in validated]
        if len(ids) != len(set(ids)):
            raise ValueError("同一批次不能重复录入同一学生")
        return validated

    @model_validator(mode="after")
    def monthly_defaults(self):
        if not self.exam_month:
            self.exam_month = self.exam_date.strftime("%Y-%m")
        if not self.exam_name.strip():
            self.exam_name = f"{self.exam_month}月考"
        return self


class WeeklyTestScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    class_id: int
    student_id: int
    subject: str
    exam_date: date
    exam_month: str = Field(default="", pattern=r"^(?:[0-9]{4}-(?:0[1-9]|1[0-2]))?$")
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
    subject: str = ""
    exam_date: date
    exam_month: str = Field(default="", pattern=r"^(?:[0-9]{4}-(?:0[1-9]|1[0-2]))?$")
    exam_name: str
    score: float
    max_score: float


class ClassWeeklySummary(BaseModel):
    exam_date: date
    exam_month: str = Field(default="", pattern=r"^(?:[0-9]{4}-(?:0[1-9]|1[0-2]))?$")
    exam_name: str
    subject: str
    avg_score: float
    max_score: float
    min_score: float
    count: int
