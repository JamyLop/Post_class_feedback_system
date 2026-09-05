"""add student consultant teacher links

Revision ID: m4n5o6p7q8r9
Revises: l3m4n5o6p7q8
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "m4n5o6p7q8r9"
down_revision: Union[str, None] = "l3m4n5o6p7q8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("subject_plans", sa.Column("teacher_name", sa.String(64), nullable=False, server_default=""))
    op.create_table(
        "student_consultants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("consultant_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("consultant_id", "student_id", name="uq_student_consultant"),
    )
    op.create_index("ix_student_consultants_consultant_id", "student_consultants", ["consultant_id"])
    op.create_index("ix_student_consultants_student_id", "student_consultants", ["student_id"])
    op.create_table(
        "subject_suggestions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_case_id", sa.Integer(), sa.ForeignKey("student_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject", sa.String(32), nullable=False),
        sa.Column("teacher_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_subject_suggestions_student_case_id", "subject_suggestions", ["student_case_id"])
    op.create_index("ix_subject_suggestions_teacher_id", "subject_suggestions", ["teacher_id"])


def downgrade() -> None:
    op.drop_column("subject_plans", "teacher_name")
    op.drop_index("ix_subject_suggestions_teacher_id", table_name="subject_suggestions")
    op.drop_index("ix_subject_suggestions_student_case_id", table_name="subject_suggestions")
    op.drop_table("subject_suggestions")
    op.drop_index("ix_student_consultants_student_id", table_name="student_consultants")
    op.drop_index("ix_student_consultants_consultant_id", table_name="student_consultants")
    op.drop_table("student_consultants")
