"""周测成绩模型：班级维度按学科、日期记录学生分数，支持批量录入与趋势分析。"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WeeklyTestScore(Base):
    """周测成绩表：一次周测对应一名学生一门学科的一条记录。"""

    __tablename__ = "weekly_test_scores"
    __table_args__ = (
        UniqueConstraint("class_id", "student_id", "subject", "exam_date", name="uq_weekly_score_student_subject_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    subject: Mapped[str] = mapped_column(String(32), index=True)
    exam_date: Mapped[date] = mapped_column(Date, index=True)
    exam_name: Mapped[str] = mapped_column(String(64), default="")
    score: Mapped[float] = mapped_column(Float)
    max_score: Mapped[float] = mapped_column(Float, default=100)
    rank_in_class: Mapped[int | None] = mapped_column(Integer, nullable=True)
    remark: Mapped[str] = mapped_column(Text, default="")
    recorded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
