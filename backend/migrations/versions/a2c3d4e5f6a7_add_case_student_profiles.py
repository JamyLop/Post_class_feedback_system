"""add case student profiles

Revision ID: a2c3d4e5f6a7
Revises: 9f1a2b3c4d5e
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a2c3d4e5f6a7"
down_revision: Union[str, None] = "9f1a2b3c4d5e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "case_student_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "student_case_id",
            sa.Integer(),
            sa.ForeignKey("student_cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("student_name", sa.String(64), nullable=False, server_default=""),
        sa.Column("gender", sa.String(16), nullable=False, server_default=""),
        sa.Column("ethnicity", sa.String(32), nullable=False, server_default=""),
        sa.Column("source_school", sa.String(128), nullable=False, server_default=""),
        sa.Column("grade", sa.String(32), nullable=False, server_default=""),
        sa.Column("parent_evaluation", sa.Text(), nullable=False, server_default=""),
        sa.Column("primary_needs", sa.Text(), nullable=False, server_default=""),
        sa.Column("allergy_history", sa.Text(), nullable=False, server_default=""),
        sa.Column("underlying_conditions", sa.Text(), nullable=False, server_default=""),
        sa.Column("other_health_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("student_case_id", name="uq_case_student_profile_case"),
    )
    op.create_index(
        "ix_case_student_profiles_student_case_id",
        "case_student_profiles",
        ["student_case_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_case_student_profiles_student_case_id", table_name="case_student_profiles")
    op.drop_table("case_student_profiles")
