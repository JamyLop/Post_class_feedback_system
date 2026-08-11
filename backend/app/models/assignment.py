from datetime import datetime
from typing import List

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampMixin
from app.core.database import Base

ASSIGNMENT_STATUS_DRAFT = "draft"
ASSIGNMENT_STATUS_PUBLISHED = "published"
ASSIGNMENT_STATUS_CLOSED = "closed"
ASSIGNMENT_STATUS_ARCHIVED = "archived"


class Assignment(TimestampMixin, Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(128))
    subject: Mapped[str] = mapped_column(String(32))
    description: Mapped[str] = mapped_column(String(512), default="")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), default=ASSIGNMENT_STATUS_DRAFT)

    questions: Mapped[List["AssignmentQuestion"]] = relationship(
        back_populates="assignment",
        cascade="all, delete-orphan",
        order_by="AssignmentQuestion.question_order",
    )


class AssignmentQuestion(Base):
    __tablename__ = "assignment_questions"

    assignment_id: Mapped[int] = mapped_column(
        ForeignKey("assignments.id", ondelete="CASCADE"), primary_key=True
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True
    )
    question_order: Mapped[int] = mapped_column(Integer, default=0)

    assignment: Mapped["Assignment"] = relationship(back_populates="questions")
