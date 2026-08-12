from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

GRADING_TYPE_RULE = "rule"
GRADING_TYPE_AI = "ai"
GRADING_TYPE_HYBRID = "hybrid"

GRADING_STATUS_PENDING = "pending"
GRADING_STATUS_AI_COMPLETED = "ai_completed"
GRADING_STATUS_MANUAL_REVIEW = "manual_review"
GRADING_STATUS_CONFIRMED = "confirmed"

# 置信度策略（实施计划第 11 节）
CONFIDENCE_MANUAL_REVIEW = 0.70
CONFIDENCE_NEED_CHECK = 0.85


class GradingResult(Base):
    __tablename__ = "grading_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_answer_id: Mapped[int] = mapped_column(
        ForeignKey("submission_answers.id", ondelete="CASCADE"), index=True
    )
    grading_type: Mapped[str] = mapped_column(String(16))
    model_name: Mapped[str] = mapped_column(String(64), default="")
    ai_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_comment: Mapped[str] = mapped_column(String(2000), default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    error_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_points: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    knowledge_points: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    raw_ai_result: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    prompt_version: Mapped[str] = mapped_column(String(32), default="")
    teacher_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    teacher_comment: Mapped[str] = mapped_column(String(2000), default="")
    status: Mapped[str] = mapped_column(String(16), default=GRADING_STATUS_PENDING)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class GradingPromptVersion(Base):
    __tablename__ = "grading_prompt_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(32))
    prompt_type: Mapped[str] = mapped_column(String(32))
    prompt: Mapped[str] = mapped_column(String(4000))
    model: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )