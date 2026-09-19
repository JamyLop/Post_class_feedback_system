"""add class school year

Revision ID: f0d4e5f6a7b8
Revises: e9c3d4e5f6a7
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f0d4e5f6a7b8"
down_revision: Union[str, None] = "e9c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "classes",
        sa.Column("school_year", sa.String(16), nullable=False, server_default="未设置"),
    )
    op.create_index("ix_classes_school_year", "classes", ["school_year"])
    op.execute("UPDATE classes SET school_year = '2026-2027' WHERE grade = '高三'")


def downgrade() -> None:
    op.drop_index("ix_classes_school_year", table_name="classes")
    op.drop_column("classes", "school_year")
