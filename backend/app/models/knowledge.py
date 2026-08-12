from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class KnowledgePoint(Base):
    __tablename__ = "knowledge_points"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject: Mapped[str] = mapped_column(String(32))
    grade: Mapped[str] = mapped_column(String(32))
    chapter: Mapped[str] = mapped_column(String(64), default="")
    name: Mapped[str] = mapped_column(String(64))
    code: Mapped[str] = mapped_column(String(64), unique=True)
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("knowledge_points.id", ondelete="CASCADE"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    children: Mapped[List["KnowledgePoint"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )
    parent: Mapped[Optional["KnowledgePoint"]] = relationship(
        back_populates="children", remote_side=[id]
    )

    def tree_path(self) -> str:
        parts = [self.name]
        node = self.parent
        while node is not None:
            parts.append(node.name)
            node = node.parent
        return " / ".join(reversed(parts))


class StudentKnowledgeRecord(Base):
    """原始学习轨迹：教师确认批改后写入，供阶段 5 聚合掌握度。

    只存原始记录，不存聚合值；保留长期数据以便未来升级掌握度算法。
    """

    __tablename__ = "student_knowledge_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    knowledge_point_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_points.id"), index=True
    )
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id"), index=True)
    is_correct: Mapped[Optional[bool]] = mapped_column(nullable=True)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    difficulty: Mapped[float] = mapped_column(Float, default=0.5)
    error_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
