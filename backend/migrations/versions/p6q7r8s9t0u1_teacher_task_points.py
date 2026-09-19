"""teacher task reminders + stage completion + points reports

Revision ID: p6q7r8s9t0u1
Revises: n5o6p7q8r9s0
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "p6q7r8s9t0u1"
down_revision: Union[str, None] = "n5o6p7q8r9s0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("case_tasks", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("case_tasks", sa.Column("points", sa.Integer(), nullable=False, server_default="10"))
    op.create_index("ix_case_tasks_version", "case_tasks", ["version"])

    op.add_column("task_checkins", sa.Column("earned_points", sa.Float(), nullable=False, server_default="0"))
    op.add_column("task_checkins", sa.Column("log_date", sa.Date(), nullable=True))
    op.create_index("ix_task_checkins_log_date", "task_checkins", ["log_date"])

    op.create_table(
        "case_stage_completions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_case_id", sa.Integer(), sa.ForeignKey("student_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("total_tasks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_tasks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_completion_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("earned_points", sa.Float(), nullable=False, server_default="0"),
        sa.Column("detail", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("recorded_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("student_case_id", "version", name="uq_stage_completion_case_version"),
    )
    op.create_index("ix_case_stage_completions_student_case_id", "case_stage_completions", ["student_case_id"])
    op.create_index("ix_case_stage_completions_version", "case_stage_completions", ["version"])

    op.create_table(
        "student_points_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("classes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_case_id", sa.Integer(), sa.ForeignKey("student_cases.id", ondelete="SET NULL"), nullable=True),
        sa.Column("period_type", sa.String(16), nullable=False),
        sa.Column("period_label", sa.String(16), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("total_points", sa.Float(), nullable=False, server_default="0"),
        sa.Column("earned_points", sa.Float(), nullable=False, server_default="0"),
        sa.Column("completion_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("task_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("checkin_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("detail", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("remark", sa.Text(), nullable=False, server_default=""),
        sa.Column("recorded_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("student_id", "period_type", "period_label", name="uq_points_report_student_period"),
    )
    op.create_index("ix_student_points_reports_student_id", "student_points_reports", ["student_id"])
    op.create_index("ix_student_points_reports_class_id", "student_points_reports", ["class_id"])
    op.create_index("ix_student_points_reports_period_type", "student_points_reports", ["period_type"])
    op.create_index("ix_student_points_reports_period_label", "student_points_reports", ["period_label"])
    op.create_index("ix_student_points_reports_period_start", "student_points_reports", ["period_start"])


def downgrade() -> None:
    op.drop_index("ix_student_points_reports_period_start", table_name="student_points_reports")
    op.drop_index("ix_student_points_reports_period_label", table_name="student_points_reports")
    op.drop_index("ix_student_points_reports_period_type", table_name="student_points_reports")
    op.drop_index("ix_student_points_reports_class_id", table_name="student_points_reports")
    op.drop_index("ix_student_points_reports_student_id", table_name="student_points_reports")
    op.drop_table("student_points_reports")
    op.drop_index("ix_case_stage_completions_version", table_name="case_stage_completions")
    op.drop_index("ix_case_stage_completions_student_case_id", table_name="case_stage_completions")
    op.drop_table("case_stage_completions")
    op.drop_index("ix_task_checkins_log_date", table_name="task_checkins")
    op.drop_column("task_checkins", "log_date")
    op.drop_column("task_checkins", "earned_points")
    op.drop_index("ix_case_tasks_version", table_name="case_tasks")
    op.drop_column("case_tasks", "points")
    op.drop_column("case_tasks", "version")
