from typing import Any, List, Optional

from sqlalchemy import JSON, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampMixin
from app.core.database import Base

# 支持的题型：客观题走规则，填空题走混合，主观题走 LLM
QUESTION_TYPES = [
    "single_choice",
    "multiple_choice",
    "judge",
    "fill",
    "calculation",
    "short_answer",
]


class Question(TimestampMixin, Base):
    """题库表：题干、标准答案、题型与评分规则。"""

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject: Mapped[str] = mapped_column(String(32))
    grade: Mapped[str] = mapped_column(String(32))
    question_type: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(String(2000))
    standard_answer: Mapped[str] = mapped_column(String(2000), default="")
    score: Mapped[float] = mapped_column(Float, default=0)
    difficulty: Mapped[float] = mapped_column(Float, default=0.5)
    grading_rule: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)

    knowledge_points: Mapped[List["QuestionKnowledgePoint"]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )


class QuestionKnowledgePoint(Base):
    """题目-知识点关联表：每题的考点及权重。"""

    __tablename__ = "question_knowledge_points"

    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True
    )
    knowledge_point_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_points.id", ondelete="CASCADE"), primary_key=True
    )
    weight: Mapped[float] = mapped_column(Float, default=1.0)

    question: Mapped["Question"] = relationship(back_populates="knowledge_points")
