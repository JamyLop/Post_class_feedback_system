"""add monthly reports

Revision ID: 9f1a2b3c4d5e
Revises: bcf685408f59
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "9f1a2b3c4d5e"
down_revision: Union[str, None] = "bcf685408f59"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "monthly_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("classes.id"), nullable=False),
        sa.Column("student_case_id", sa.Integer(), sa.ForeignKey("student_cases.id"), nullable=True),
        sa.Column("month_label", sa.String(16), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="generating"),
        sa.Column("input_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("ai_content", sa.Text(), nullable=False, server_default=""),
        sa.Column("final_content", sa.Text(), nullable=False, server_default=""),
        sa.Column("model_name", sa.String(64), nullable=False, server_default=""),
        sa.Column("prompt_version", sa.String(32), nullable=False, server_default="monthly_v1"),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("student_id", "class_id", "month_label", name="uq_monthly_report_student_month"),
    )
    op.create_index("ix_monthly_reports_student_id", "monthly_reports", ["student_id"])
    op.create_index("ix_monthly_reports_class_id", "monthly_reports", ["class_id"])
    op.create_index("ix_monthly_reports_month_label", "monthly_reports", ["month_label"])
    op.create_index("ix_monthly_reports_status", "monthly_reports", ["status"])
    op.create_index("ix_monthly_reports_period_start", "monthly_reports", ["period_start"])
    op.create_index("ix_monthly_reports_student_case_id", "monthly_reports", ["student_case_id"])


def downgrade() -> None:
    op.drop_index("ix_monthly_reports_student_case_id", table_name="monthly_reports")
    op.drop_index("ix_monthly_reports_period_start", table_name="monthly_reports")
    op.drop_index("ix_monthly_reports_status", table_name="monthly_reports")
    op.drop_index("ix_monthly_reports_month_label", table_name="monthly_reports")
    op.drop_index("ix_monthly_reports_class_id", table_name="monthly_reports")
    op.drop_index("ix_monthly_reports_student_id", table_name="monthly_reports")
    op.drop_table("monthly_reports")
