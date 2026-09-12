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
    weekly_times: int | None = None
    starts_on: date | None = None
    due_on: date | None = None
    status: str = ""
    version: int = 1
    points: int = 1
    overdue_days: int = 0
    logged_today: bool = False


class RevisionCaseItem(BaseModel):
    case_id: int
    student_id: int
    student_name: str | None = None
    class_id: int
    class_name: str | None = None
    version: int = 1
    problem: str = ""
    corrective_action: str = ""
    correction_due_on: date | None = None


class NextWeekMissingItem(BaseModel):
    """下周待建周任务的档案：下周一起止范围内没有生效中周计划任务覆盖。"""

    case_id: int
    student_id: int
    student_name: str | None = None
    class_id: int
    class_name: str | None = None
    version: int = 1
    case_status: str = ""
    # 该档案生效中的周计划任务总数（供班主任判断是补建还是新建）
    active_weekly_count: int = 0


class WeeklyPointsOut(BaseModel):
    """单个档案本周积分：自然周（周一~周日）内打卡积分。

    口径与积分周报一致：每天每任务满分 1 分按完成度折算，
    同一任务同一天仅取最新一条，单科单日封顶 1 分、单科周封顶 7 分。
    """

    week_label: str
    starts_on: date
    ends_on: date
    earned_points: float = 0.0
    per_subject_earned: dict[str, float] = {}
    checkin_count: int = 0


class TaskRemindersOut(BaseModel):
    date: date
    overdue: list[ReminderTaskItem] = []
    due_today: list[ReminderTaskItem] = []
    unlogged_today: list[ReminderTaskItem] = []
    needs_revision: list[RevisionCaseItem] = []
    # 下周（周一~周日）尚无周计划任务覆盖的档案：提醒班主任提前建好下周周任务
    next_week_starts_on: date | None = None
    next_week_ends_on: date | None = None
    next_week_missing: list[NextWeekMissingItem] = []
    counts: dict[str, int] = {}


class BatchCheckinItem(BaseModel):
    task_id: int
    # 打卡即得满分 1 分：前端不再填写完成度，缺省按 100% 计。
    completion_rate: int = Field(default=100, ge=0, le=100)
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
    # 报表抬头使用班主任署名；班主任关系优先于 classes.teacher_id 的旧字段。
    head_teacher_name: str | None = None


class PointsReportBuildIn(BaseModel):
    class_id: int
    # weekly: 2026-W36；monthly: 2026-09；缺省为当前周/月
    period_label: str | None = None
    period_type: Literal["weekly", "monthly"] = "weekly"
