"""add subject to users (subject teacher field)

Revision ID: r8s9t0u1v2w3
Revises: q7r8s9t0u1v2
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "r8s9t0u1v2w3"
down_revision: Union[str, None] = "q7r8s9t0u1v2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("subject", sa.String(32), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("users", "subject")
