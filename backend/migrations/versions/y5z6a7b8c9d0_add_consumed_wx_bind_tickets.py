"""add durable consumed wx bind tickets

Revision ID: y5z6a7b8c9d0
Revises: w3x4y5z6a7b8
Create Date: 2026-09-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "y5z6a7b8c9d0"
down_revision: Union[str, None] = "w3x4y5z6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "consumed_wx_bind_tickets",
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("jti"),
    )
    op.create_index("ix_consumed_wx_bind_tickets_expires_at", "consumed_wx_bind_tickets", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_consumed_wx_bind_tickets_expires_at", table_name="consumed_wx_bind_tickets")
    op.drop_table("consumed_wx_bind_tickets")
