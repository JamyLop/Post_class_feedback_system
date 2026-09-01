"""月度评价模型：按自然月汇总学情与德育状态，AI初稿 + 班主任可编辑发布。"""

from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

MONTHLY_STATUS_GENERATING = "generating"
MONTHLY_STATUS_GENERATED = "generated"
MONTHLY_STATUS_PUBLISHED = "published"
MONTHLY_STATUS_FAILED = "failed"


class MonthlyReport(Base):
    """学生月度评价表：一个月一份，记录AI输入快照与教师定稿。"""

    __tablename__ = "monthly_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), index=True)
    student_case_id: Mapped[int | None] = mapped_column(ForeignKey("student_cases.id"), nullable=True, index=True)
    # 自然月标识，如 2026-08，便于按月查询与幂等
    month_label: Mapped[str] = mapped_column(String(16), index=True)
    period_start: Mapped[date] = mapped_column(Date, index=True)
    period_end: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(16), default=MONTHLY_STATUS_GENERATING, index=True)
    input_snapshot: Mapped[Any] = mapped_column(JSON, default=dict)
    ai_content: Mapped[str] = mapped_column(Text, default="")
    final_content: Mapped[str] = mapped_column(Text, default="")
    model_name: Mapped[str] = mapped_column(String(64), default="")
    prompt_version: Mapped[str] = mapped_column(String(32), default="monthly_v1")
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str] = mapped_column(Text, default="")
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
