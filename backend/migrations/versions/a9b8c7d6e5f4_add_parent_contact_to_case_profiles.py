"""add parent contact to case profiles

Revision ID: a9b8c7d6e5f4
Revises: f0d4e5f6a7b8
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a9b8c7d6e5f4"
down_revision: Union[str, None] = "f0d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "case_student_profiles",
        sa.Column("parent_name", sa.String(64), nullable=False, server_default=""),
    )
    op.add_column(
        "case_student_profiles",
        sa.Column("parent_phone", sa.String(32), nullable=False, server_default=""),
    )
    op.add_column(
        "case_student_profiles",
        sa.Column("parent_relationship", sa.String(24), nullable=False, server_default=""),
    )
    op.create_index("ix_case_student_profiles_parent_phone", "case_student_profiles", ["parent_phone"])


def downgrade() -> None:
    op.drop_index("ix_case_student_profiles_parent_phone", table_name="case_student_profiles")
    op.drop_column("case_student_profiles", "parent_relationship")
    op.drop_column("case_student_profiles", "parent_phone")
    op.drop_column("case_student_profiles", "parent_name")
