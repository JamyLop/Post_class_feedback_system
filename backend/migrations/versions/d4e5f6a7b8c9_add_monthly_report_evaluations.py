"""Add independent teacher evaluations to monthly reports.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b9
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "monthly_report_evaluations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("report_id", sa.Integer(), sa.ForeignKey("monthly_reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("teacher_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("teacher_name", sa.String(64), nullable=False),
        sa.Column("teacher_role", sa.String(24), nullable=False),
        sa.Column("subject", sa.String(32), nullable=False, server_default=""),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("report_id", "teacher_id", name="uq_monthly_evaluation_report_teacher"),
    )
    op.create_index("ix_monthly_report_evaluations_report_id", "monthly_report_evaluations", ["report_id"])
    op.create_index("ix_monthly_report_evaluations_teacher_id", "monthly_report_evaluations", ["teacher_id"])


def downgrade() -> None:
    op.drop_table("monthly_report_evaluations")
