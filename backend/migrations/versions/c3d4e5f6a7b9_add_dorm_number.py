"""add dorm number to student info

Revision ID: c3d4e5f6a7b9
Revises: b2c3d4e5f6a8
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c3d4e5f6a7b9"
down_revision: Union[str, None] = "b2c3d4e5f6a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("dorm_number", sa.String(32), nullable=False, server_default=""),
    )
    op.add_column(
        "case_student_profiles",
        sa.Column("dorm_number", sa.String(32), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("case_student_profiles", "dorm_number")
    op.drop_column("users", "dorm_number")
