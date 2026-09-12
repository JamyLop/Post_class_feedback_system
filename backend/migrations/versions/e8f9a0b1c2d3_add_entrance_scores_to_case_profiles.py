"""add entrance_scores to case profiles (merge heads)

Revision ID: e8f9a0b1c2d3
Revises: c8d9e0f1a2b3, a9b8c7d6e5f4
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e8f9a0b1c2d3"
down_revision: Union[str, Sequence[str], None] = ("c8d9e0f1a2b3", "a9b8c7d6e5f4")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "case_student_profiles",
        sa.Column("entrance_scores", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("case_student_profiles", "entrance_scores")
