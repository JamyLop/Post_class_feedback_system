"""add feedback_reports

Revision ID: 4e4d9f8a2b6c
Revises: 8cede53c312e
Create Date: 2026-08-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "4e4d9f8a2b6c"
down_revision: Union[str, None] = "8cede53c312e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "feedback_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("class_id", sa.Integer(), nullable=False),
        sa.Column("assignment_id", sa.Integer(), nullable=True),
        sa.Column("report_type", sa.String(length=16), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("input_snapshot", sa.JSON(), nullable=False),
        sa.Column("ai_content", sa.Text(), nullable=False),
        sa.Column("final_content", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(length=64), nullable=False),
        sa.Column("prompt_version", sa.String(length=32), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assignment_id"], ["assignments.id"]),
        sa.ForeignKeyConstraint(["class_id"], ["classes.id"]),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_feedback_reports_student_id", "feedback_reports", ["student_id"])
    op.create_index("ix_feedback_reports_class_id", "feedback_reports", ["class_id"])
    op.create_index("ix_feedback_reports_assignment_id", "feedback_reports", ["assignment_id"])
    op.create_index("ix_feedback_reports_report_type", "feedback_reports", ["report_type"])


def downgrade() -> None:
    op.drop_index("ix_feedback_reports_report_type", table_name="feedback_reports")
    op.drop_index("ix_feedback_reports_assignment_id", table_name="feedback_reports")
    op.drop_index("ix_feedback_reports_class_id", table_name="feedback_reports")
    op.drop_index("ix_feedback_reports_student_id", table_name="feedback_reports")
    op.drop_table("feedback_reports")
