"""阶段任务完成度与积分周报/月报模型。

阶段口径：总案 version（每次阶段复盘 adjusted +1 即新阶段）。
积分口径：task.points（满分积分/权重）× 打卡 completion_rate% = earned_points。
"""

from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin


class CaseStageCompletion(TimestampMixin, Base):
    """每个阶段（case_id + version）的任务完成度记录，打卡后自动重算。"""

    __tablename__ = "case_stage_completions"
    __table_args__ = (
        UniqueConstraint("student_case_id", "version", name="uq_stage_completion_case_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_case_id: Mapped[int] = mapped_column(
        ForeignKey("student_cases.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer, index=True)
    total_tasks: Mapped[int] = mapped_column(Integer, default=0)
    completed_tasks: Mapped[int] = mapped_column(Integer, default=0)
    avg_completion_rate: Mapped[float] = mapped_column(Float, default=0.0)
    total_points: Mapped[int] = mapped_column(Integer, default=0)
    earned_points: Mapped[float] = mapped_column(Float, default=0.0)
    detail: Mapped[Any] = mapped_column(JSON, default=dict)
    recorded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)


PERIOD_WEEKLY = "weekly"
PERIOD_MONTHLY = "monthly"


class StudentPointsReport(TimestampMixin, Base):
    """积分周报/月报：按周期从每日打卡累加 earned_points，一学生一周期一条。"""

    __tablename__ = "student_points_reports"
    __table_args__ = (
        UniqueConstraint(
            "student_id", "period_type", "period_label",
            name="uq_points_report_student_period",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), index=True)
    student_case_id: Mapped[int | None] = mapped_column(
        ForeignKey("student_cases.id", ondelete="SET NULL"), nullable=True, index=True
    )
    period_type: Mapped[str] = mapped_column(String(16), index=True)
    # weekly: 2026-W36；monthly: 2026-09
    period_label: Mapped[str] = mapped_column(String(16), index=True)
    period_start: Mapped[date] = mapped_column(Date, index=True)
    period_end: Mapped[date] = mapped_column(Date, index=True)
    total_points: Mapped[float] = mapped_column(Float, default=0.0)
    earned_points: Mapped[float] = mapped_column(Float, default=0.0)
    completion_rate: Mapped[float] = mapped_column(Float, default=0.0)
    task_count: Mapped[int] = mapped_column(Integer, default=0)
    checkin_count: Mapped[int] = mapped_column(Integer, default=0)
    detail: Mapped[Any] = mapped_column(JSON, default=dict)
    remark: Mapped[str] = mapped_column(Text, default="")
    recorded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
