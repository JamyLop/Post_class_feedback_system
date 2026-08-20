from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# 批改类型：规则 / AI / 混合
GRADING_TYPE_RULE = "rule"
GRADING_TYPE_AI = "ai"
GRADING_TYPE_HYBRID = "hybrid"

# 批改状态：待批 → AI 完成 → 人工复核 → 已确认
GRADING_STATUS_PENDING = "pending"
GRADING_STATUS_AI_COMPLETED = "ai_completed"
GRADING_STATUS_MANUAL_REVIEW = "manual_review"
GRADING_STATUS_CONFIRMED = "confirmed"

# 置信度策略（实施计划第 11 节）
CONFIDENCE_MANUAL_REVIEW = 0.70
CONFIDENCE_NEED_CHECK = 0.85


class GradingResult(Base):
    """批改结果表：逐题一条，含 AI 输出、教师复核与置信度。"""

    __tablename__ = "grading_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_answer_id: Mapped[int] = mapped_column(
        ForeignKey("submission_answers.id", ondelete="CASCADE"),
        unique=True,
        index=True,
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
    """Prompt 版本追踪表：记录每次使用的批改提示词版本。"""

    __tablename__ = "grading_prompt_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(32))
    prompt_type: Mapped[str] = mapped_column(String(32))
    prompt: Mapped[str] = mapped_column(String(4000))
    model: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )