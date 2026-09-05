"""阶段完成度、任务提醒与积分周报/月报的请求响应模型。"""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StageCompletionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_case_id: int
    version: int
    total_tasks: int
    completed_tasks: int
    avg_completion_rate: float
    total_points: int
    earned_points: float
    detail: Any = None
    recorded_by: int | None = None
    created_at: datetime
    updated_at: datetime


class ReminderTaskItem(BaseModel):
    task_id: int
    case_id: int
    student_id: int
    student_name: str | None = None
    class_id: int
    class_name: str | None = None
    subject: str = ""
    title: str
    cadence: str = ""
    starts_on: date | None = None
    due_on: date | None = None
    status: str = ""
    version: int = 1
    points: int = 10
    overdue_days: int = 0
    logged_today: bool = False


class TaskRemindersOut(BaseModel):
    date: date
    overdue: list[ReminderTaskItem] = []
    due_today: list[ReminderTaskItem] = []
    unlogged_today: list[ReminderTaskItem] = []
    counts: dict[str, int] = {}


class BatchCheckinItem(BaseModel):
    task_id: int
    completion_rate: int = Field(ge=0, le=100)
    self_check: str = Field(default="", max_length=2000)


class BatchCheckinCreate(BaseModel):
    log_date: date | None = None
    items: list[BatchCheckinItem] = Field(min_length=1)


class PointsReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    class_id: int
    student_case_id: int | None = None
    period_type: str
    period_label: str
    period_start: date
    period_end: date
    total_points: float
    earned_points: float
    completion_rate: float
    task_count: int
    checkin_count: int
    detail: Any = None
    remark: str = ""
    student_name: str | None = None
    class_name: str | None = None


class PointsReportBuildIn(BaseModel):
    class_id: int
    # weekly: 2026-W36；monthly: 2026-09；缺省为当前周/月
    period_label: str | None = None
    period_type: Literal["weekly", "monthly"] = "weekly"
