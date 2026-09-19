"""add checkin attachments

Revision ID: t0u1v2w3x4y5
Revises: s9t0u1v2w3x4
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "t0u1v2w3x4y5"
down_revision: Union[str, None] = "s9t0u1v2w3x4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("task_checkins", sa.Column("attachments", sa.JSON(), nullable=False, server_default="[]"))


def downgrade() -> None:
    op.drop_column("task_checkins", "attachments")
