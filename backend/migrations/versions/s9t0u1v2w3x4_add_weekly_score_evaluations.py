"""Add independent teacher evaluations to weekly scores.

Revision ID: s9t0u1v2w3x4
Revises: r8s9t0u1v2w3
"""

from alembic import op
import sqlalchemy as sa

revision = "s9t0u1v2w3x4"
down_revision = "r8s9t0u1v2w3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "weekly_score_evaluations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("score_id", sa.Integer(), sa.ForeignKey("weekly_test_scores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("teacher_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("teacher_name", sa.String(64), nullable=False),
        sa.Column("teacher_role", sa.String(24), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("score_id", "teacher_id", name="uq_weekly_evaluation_score_teacher"),
    )
    op.create_index("ix_weekly_score_evaluations_score_id", "weekly_score_evaluations", ["score_id"])
    op.create_index("ix_weekly_score_evaluations_teacher_id", "weekly_score_evaluations", ["teacher_id"])


def downgrade() -> None:
    op.drop_table("weekly_score_evaluations")
