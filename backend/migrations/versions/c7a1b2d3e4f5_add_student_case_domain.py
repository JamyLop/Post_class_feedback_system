"""add student case domain

Revision ID: c7a1b2d3e4f5
Revises: a1b2c3d4e5f6
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c7a1b2d3e4f5"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "class_teachers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("classes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("teacher_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(24), nullable=False, server_default="subject_teacher"),
        sa.Column("subject", sa.String(32), nullable=False, server_default=""),
        *_timestamps(),
        sa.UniqueConstraint("class_id", "teacher_id", "subject", name="uq_class_teacher_subject"),
    )
    op.create_index("ix_class_teachers_class_id", "class_teachers", ["class_id"])
    op.create_index("ix_class_teachers_teacher_id", "class_teachers", ["teacher_id"])

    op.create_table(
        "case_cycles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("grade", sa.String(16), nullable=False, server_default="高三"),
        sa.Column("school_year", sa.String(16), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_timestamps(),
    )
    op.create_index("ix_case_cycles_grade", "case_cycles", ["grade"])
    op.create_index("ix_case_cycles_school_year", "case_cycles", ["school_year"])
    op.create_index("ix_case_cycles_is_active", "case_cycles", ["is_active"])

    op.create_table(
        "student_cases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cycle_id", sa.Integer(), sa.ForeignKey("case_cycles.id"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("classes.id"), nullable=False),
        sa.Column("owner_teacher_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("overall_problem", sa.Text(), nullable=False, server_default=""),
        sa.Column("admission_target", sa.Text(), nullable=False, server_default=""),
        sa.Column("current_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        *_timestamps(),
        sa.UniqueConstraint("cycle_id", "student_id", name="uq_student_case_cycle_student"),
    )
    for column in ("cycle_id", "student_id", "class_id", "owner_teacher_id", "status"):
        op.create_index(f"ix_student_cases_{column}", "student_cases", [column])

    op.create_table(
        "case_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_case_id", sa.Integer(), sa.ForeignKey("student_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("change_reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("student_case_id", "version", name="uq_case_version_number"),
    )
    op.create_index("ix_case_versions_student_case_id", "case_versions", ["student_case_id"])

    op.create_table(
        "subject_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_case_id", sa.Integer(), sa.ForeignKey("student_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject", sa.String(32), nullable=False),
        sa.Column("teacher_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("problem_location", sa.Text(), nullable=False, server_default=""),
        sa.Column("cause_analysis", sa.Text(), nullable=False, server_default=""),
        sa.Column("struggle_goal", sa.Text(), nullable=False, server_default=""),
        sa.Column("gaokao_requirement", sa.Text(), nullable=False, server_default=""),
        sa.Column("reinforcement", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(24), nullable=False, server_default="draft"),
        *_timestamps(),
        sa.UniqueConstraint("student_case_id", "subject", name="uq_case_subject_plan"),
    )
    for column in ("student_case_id", "subject", "teacher_id"):
        op.create_index(f"ix_subject_plans_{column}", "subject_plans", [column])

    op.create_table(
        "case_diagnoses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_case_id", sa.Integer(), sa.ForeignKey("student_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject", sa.String(32), nullable=False, server_default=""),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("is_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("confirmed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        *_timestamps(),
    )
    for column in ("student_case_id", "subject", "is_confirmed"):
        op.create_index(f"ix_case_diagnoses_{column}", "case_diagnoses", [column])

    op.create_table(
        "case_goals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_case_id", sa.Integer(), sa.ForeignKey("student_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("goal_type", sa.String(32), nullable=False),
        sa.Column("subject", sa.String(32), nullable=False, server_default=""),
        sa.Column("title", sa.String(128), nullable=False),
        sa.Column("baseline_value", sa.Float(), nullable=True),
        sa.Column("target_value", sa.Float(), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default="not_started"),
        *_timestamps(),
    )
    for column in ("student_case_id", "goal_type", "subject", "status"):
        op.create_index(f"ix_case_goals_{column}", "case_goals", [column])

    op.create_table(
        "case_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_case_id", sa.Integer(), sa.ForeignKey("student_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject", sa.String(32), nullable=False, server_default=""),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("cadence", sa.String(16), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("due_on", sa.Date(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        *_timestamps(),
    )
    for column in ("student_case_id", "subject", "cadence", "due_on", "status"):
        op.create_index(f"ix_case_tasks_{column}", "case_tasks", [column])

    op.create_table(
        "task_checkins",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("case_tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("completion_rate", sa.Integer(), nullable=False),
        sa.Column("self_check", sa.Text(), nullable=False, server_default=""),
        sa.Column("checked_in_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_task_checkins_task_id", "task_checkins", ["task_id"])
    op.create_index("ix_task_checkins_student_id", "task_checkins", ["student_id"])

    op.create_table(
        "case_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_case_id", sa.Integer(), sa.ForeignKey("student_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("case_tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("review_level", sa.String(24), nullable=False),
        sa.Column("subject", sa.String(32), nullable=False, server_default=""),
        sa.Column("reviewer_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("problem", sa.Text(), nullable=False, server_default=""),
        sa.Column("corrective_action", sa.Text(), nullable=False, server_default=""),
        sa.Column("correction_due_on", sa.Date(), nullable=True),
        sa.Column("recheck_result", sa.Text(), nullable=False, server_default=""),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    for column in ("student_case_id", "task_id", "review_level", "reviewer_id"):
        op.create_index(f"ix_case_reviews_{column}", "case_reviews", [column])

    op.create_table(
        "case_evidence_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_case_id", sa.Integer(), sa.ForeignKey("student_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("diagnosis_id", sa.Integer(), sa.ForeignKey("case_diagnoses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("evidence_type", sa.String(32), nullable=False),
        sa.Column("source_id", sa.String(128), nullable=False),
        sa.Column("title", sa.String(160), nullable=False, server_default=""),
        sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("linked_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("student_case_id", "evidence_type", "source_id", name="uq_case_evidence_source"),
    )
    op.create_index("ix_case_evidence_links_student_case_id", "case_evidence_links", ["student_case_id"])
    op.create_index("ix_case_evidence_links_evidence_type", "case_evidence_links", ["evidence_type"])

    op.create_table(
        "case_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_case_id", sa.Integer(), sa.ForeignKey("student_cases.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("detail", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    for column in ("student_case_id", "actor_id", "action"):
        op.create_index(f"ix_case_audit_logs_{column}", "case_audit_logs", [column])


def downgrade() -> None:
    for table in (
        "case_audit_logs", "case_evidence_links", "case_reviews", "task_checkins",
        "case_tasks", "case_goals", "case_diagnoses", "subject_plans", "case_versions",
        "student_cases", "case_cycles", "class_teachers",
    ):
        op.drop_table(table)
