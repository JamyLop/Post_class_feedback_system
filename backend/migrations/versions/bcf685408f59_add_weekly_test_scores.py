"""add weekly test scores

Revision ID: bcf685408f59
Revises: f0d4e5f6a7b8
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "bcf685408f59"
down_revision: Union[str, None] = "f0d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "weekly_test_scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("classes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject", sa.String(32), nullable=False),
        sa.Column("exam_date", sa.Date(), nullable=False),
        sa.Column("exam_name", sa.String(64), nullable=False, server_default=""),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("max_score", sa.Float(), nullable=False, server_default="100"),
        sa.Column("rank_in_class", sa.Integer(), nullable=True),
        sa.Column("remark", sa.Text(), nullable=False, server_default=""),
        sa.Column("recorded_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("class_id", "student_id", "subject", "exam_date", name="uq_weekly_score_student_subject_date"),
    )
    op.create_index("ix_weekly_test_scores_class_id", "weekly_test_scores", ["class_id"])
    op.create_index("ix_weekly_test_scores_student_id", "weekly_test_scores", ["student_id"])
    op.create_index("ix_weekly_test_scores_subject", "weekly_test_scores", ["subject"])
    op.create_index("ix_weekly_test_scores_exam_date", "weekly_test_scores", ["exam_date"])
    op.create_index("ix_weekly_test_scores_recorded_by", "weekly_test_scores", ["recorded_by"])


def downgrade() -> None:
    op.drop_index("ix_weekly_test_scores_recorded_by", table_name="weekly_test_scores")
    op.drop_index("ix_weekly_test_scores_exam_date", table_name="weekly_test_scores")
    op.drop_index("ix_weekly_test_scores_subject", table_name="weekly_test_scores")
    op.drop_index("ix_weekly_test_scores_student_id", table_name="weekly_test_scores")
    op.drop_index("ix_weekly_test_scores_class_id", table_name="weekly_test_scores")
    op.drop_table("weekly_test_scores")
