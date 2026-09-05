"""add wx external identities

Revision ID: i9j0k1l2m3n4
Revises: h2i3j4k5l6m7
Create Date: 2026-08-31

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "i9j0k1l2m3n4"
down_revision: Union[str, None] = "h2i3j4k5l6m7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_external_identities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False, server_default="wechat_miniprogram"),
        sa.Column("app_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("subject_id", sa.String(128), nullable=False),
        sa.Column("unionid", sa.String(128), nullable=True),
        sa.Column("bound_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("provider", "app_id", "subject_id", name="uq_provider_app_subject"),
        sa.UniqueConstraint("provider", "user_id", name="uq_provider_user"),
    )
    op.create_index("ix_user_external_identities_user_id", "user_external_identities", ["user_id"])
    op.create_index("ix_user_external_identities_provider", "user_external_identities", ["provider"])
    op.create_index("ix_user_external_identities_app_id", "user_external_identities", ["app_id"])
    op.create_index("ix_user_external_identities_subject_id", "user_external_identities", ["subject_id"])


def downgrade() -> None:
    op.drop_index("ix_user_external_identities_subject_id", table_name="user_external_identities")
    op.drop_index("ix_user_external_identities_app_id", table_name="user_external_identities")
    op.drop_index("ix_user_external_identities_provider", table_name="user_external_identities")
    op.drop_index("ix_user_external_identities_user_id", table_name="user_external_identities")
    op.drop_table("user_external_identities")
