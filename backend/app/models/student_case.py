"""高三一生一案领域模型。

第一版坚持追加式演进：新表只关联现有用户、班级和作业证据，不改写旧批改表。
"""

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin

CASE_STATUS_DRAFT = "draft"
CASE_STATUS_PENDING_CONFIRMATION = "pending_confirmation"
CASE_STATUS_EXECUTING = "executing"
CASE_STATUS_PENDING_REVIEW = "pending_review"
CASE_STATUS_ADJUSTED = "adjusted"
CASE_STATUS_ARCHIVED = "archived"

CASE_STATUSES = (
    CASE_STATUS_DRAFT,
    CASE_STATUS_PENDING_CONFIRMATION,
    CASE_STATUS_EXECUTING,
    CASE_STATUS_PENDING_REVIEW,
    CASE_STATUS_ADJUSTED,
    CASE_STATUS_ARCHIVED,
)


class CaseCycle(TimestampMixin, Base):
    __tablename__ = "case_cycles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    grade: Mapped[str] = mapped_column(String(16), default="高三", index=True)
    school_year: Mapped[str] = mapped_column(String(16), index=True)
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class StudentCase(TimestampMixin, Base):
    __tablename__ = "student_cases"
    __table_args__ = (
        UniqueConstraint("cycle_id", "student_id", name="uq_student_case_cycle_student"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("case_cycles.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), index=True)
    owner_teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    overall_problem: Mapped[str] = mapped_column(Text, default="")
    admission_target: Mapped[str] = mapped_column(Text, default="")
    current_summary: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default=CASE_STATUS_DRAFT, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)


class CaseVersion(Base):
    """不可变版本快照；服务层只允许插入和读取。"""

    __tablename__ = "case_versions"
    __table_args__ = (
        UniqueConstraint("student_case_id", "version", name="uq_case_version_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_case_id: Mapped[int] = mapped_column(
        ForeignKey("student_cases.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[Any] = mapped_column(JSON)
    change_reason: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class SubjectPlan(TimestampMixin, Base):
    __tablename__ = "subject_plans"
    __table_args__ = (
        UniqueConstraint("student_case_id", "subject", name="uq_case_subject_plan"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_case_id: Mapped[int] = mapped_column(
        ForeignKey("student_cases.id", ondelete="CASCADE"), index=True
    )
    subject: Mapped[str] = mapped_column(String(32), index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    problem_location: Mapped[str] = mapped_column(Text, default="")
    cause_analysis: Mapped[str] = mapped_column(Text, default="")
    struggle_goal: Mapped[str] = mapped_column(Text, default="")
    gaokao_requirement: Mapped[str] = mapped_column(Text, default="")
    reinforcement: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(24), default="draft")


class CaseDiagnosis(TimestampMixin, Base):
    __tablename__ = "case_diagnoses"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_case_id: Mapped[int] = mapped_column(
        ForeignKey("student_cases.id", ondelete="CASCADE"), index=True
    )
    subject: Mapped[str] = mapped_column(String(32), default="", index=True)
    category: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(32), default="manual")
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    confirmed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class CaseGoal(TimestampMixin, Base):
    __tablename__ = "case_goals"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_case_id: Mapped[int] = mapped_column(
        ForeignKey("student_cases.id", ondelete="CASCADE"), index=True
    )
    goal_type: Mapped[str] = mapped_column(String(32), index=True)
    subject: Mapped[str] = mapped_column(String(32), default="", index=True)
    title: Mapped[str] = mapped_column(String(128))
    baseline_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="not_started", index=True)


class CaseTask(TimestampMixin, Base):
    __tablename__ = "case_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_case_id: Mapped[int] = mapped_column(
        ForeignKey("student_cases.id", ondelete="CASCADE"), index=True
    )
    subject: Mapped[str] = mapped_column(String(32), default="", index=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    cadence: Mapped[str] = mapped_column(String(16), index=True)
    starts_on: Mapped[date] = mapped_column(Date)
    due_on: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))


class TaskCheckin(Base):
    __tablename__ = "task_checkins"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("case_tasks.id", ondelete="CASCADE"), index=True
    )
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    completion_rate: Mapped[int] = mapped_column(Integer)
    self_check: Mapped[str] = mapped_column(Text, default="")
    checked_in_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class CaseReview(Base):
    __tablename__ = "case_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_case_id: Mapped[int] = mapped_column(
        ForeignKey("student_cases.id", ondelete="CASCADE"), index=True
    )
    task_id: Mapped[int | None] = mapped_column(
        ForeignKey("case_tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    review_level: Mapped[str] = mapped_column(String(24), index=True)
    subject: Mapped[str] = mapped_column(String(32), default="")
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    problem: Mapped[str] = mapped_column(Text, default="")
    corrective_action: Mapped[str] = mapped_column(Text, default="")
    correction_due_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    recheck_result: Mapped[str] = mapped_column(Text, default="")
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class CaseEvidenceLink(Base):
    __tablename__ = "case_evidence_links"
    __table_args__ = (
        UniqueConstraint(
            "student_case_id", "evidence_type", "source_id", name="uq_case_evidence_source"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_case_id: Mapped[int] = mapped_column(
        ForeignKey("student_cases.id", ondelete="CASCADE"), index=True
    )
    diagnosis_id: Mapped[int | None] = mapped_column(
        ForeignKey("case_diagnoses.id", ondelete="SET NULL"), nullable=True
    )
    evidence_type: Mapped[str] = mapped_column(String(32), index=True)
    source_id: Mapped[str] = mapped_column(String(128))
    title: Mapped[str] = mapped_column(String(160), default="")
    payload: Mapped[Any] = mapped_column(JSON, default=dict)
    linked_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class CaseAuditLog(Base):
    __tablename__ = "case_audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_case_id: Mapped[int | None] = mapped_column(
        ForeignKey("student_cases.id", ondelete="SET NULL"), nullable=True, index=True
    )
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str] = mapped_column(String(64), default="")
    detail: Mapped[Any] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class CaseImportBatch(Base):
    """历史材料导入批次；batch_key 保证同一次试导入可安全重跑。"""

    __tablename__ = "case_import_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_key: Mapped[str] = mapped_column(String(96), unique=True, index=True)
    scope_grade: Mapped[str] = mapped_column(String(16), default="高三")
    source_root: Mapped[str] = mapped_column(Text)
    selected_students: Mapped[Any] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(24), default="processing", index=True)
    summary: Mapped[Any] = mapped_column(JSON, default=dict)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class CaseImportDocument(Base):
    """每个源文件独立保留；同内容不同路径仍是不同来源版本。"""

    __tablename__ = "case_import_documents"
    __table_args__ = (
        UniqueConstraint("batch_id", "original_path", name="uq_case_import_batch_path"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("case_import_batches.id", ondelete="CASCADE"), index=True
    )
    student_case_id: Mapped[int | None] = mapped_column(
        ForeignKey("student_cases.id", ondelete="SET NULL"), nullable=True, index=True
    )
    detected_student_name: Mapped[str] = mapped_column(String(64), index=True)
    detected_subject: Mapped[str] = mapped_column(String(32), default="")
    original_path: Mapped[str] = mapped_column(Text)
    original_filename: Mapped[str] = mapped_column(String(255))
    file_ext: Mapped[str] = mapped_column(String(16), index=True)
    file_hash: Mapped[str] = mapped_column(String(64), index=True)
    source_version: Mapped[int] = mapped_column(Integer, default=1)
    file_size: Mapped[int] = mapped_column(Integer)
    raw_text: Mapped[str] = mapped_column(Text, default="")
    parsed_fields: Mapped[Any] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), index=True)
    conflict_reason: Mapped[str] = mapped_column(Text, default="")
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
