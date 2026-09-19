"""周课表：以班级、教师和固定周次节次保存常规课程安排。"""

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin


class TimetableEntry(TimestampMixin, Base):
    __tablename__ = "timetable_entries"
    __table_args__ = (
        UniqueConstraint("class_id", "weekday", "period", name="uq_timetable_class_slot"),
        UniqueConstraint("teacher_id", "weekday", "period", name="uq_timetable_teacher_slot"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    subject: Mapped[str] = mapped_column(String(32))
    weekday: Mapped[int] = mapped_column(Integer)
    period: Mapped[int] = mapped_column(Integer)
    classroom: Mapped[str] = mapped_column(String(64), default="")
