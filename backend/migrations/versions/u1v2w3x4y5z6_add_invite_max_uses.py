"""add invite max_uses/used_count

Revision ID: u1v2w3x4y5z6
Revises: t0u1v2w3x4y5
Create Date: 2026-09-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "u1v2w3x4y5z6"
down_revision: Union[str, None] = "t0u1v2w3x4y5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("invite_codes", sa.Column("max_uses", sa.Integer(), nullable=False, server_default=sa.text("1")))
    op.add_column("invite_codes", sa.Column("used_count", sa.Integer(), nullable=False, server_default=sa.text("0")))
    # 存量回填：已使用的码计为已用 1 次（默认 max_uses=1，即用满）
    op.execute("UPDATE invite_codes SET used_count = 1 WHERE status = 'used'")


def downgrade() -> None:
    op.drop_column("invite_codes", "used_count")
    op.drop_column("invite_codes", "max_uses")
