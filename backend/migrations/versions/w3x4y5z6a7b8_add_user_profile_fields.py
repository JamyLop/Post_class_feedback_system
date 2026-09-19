"""add missing user profile fields (gender/ethnicity/source_school/grade)

Revision ID: w3x4y5z6a7b8
Revises: v2w3x4y5z6a7
Create Date: 2026-09-09

为何需要：User 模型已包含 gender/ethnicity/source_school/grade 四列
但 f8adfa... 初始建表未包含，且后续无迁移添加，导致生产库通过 alembic
升级时会缺列（测试库走 Base.metadata.create_all 不受影响）。
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'w3x4y5z6a7b8'
down_revision: Union[str, None] = 'v2w3x4y5z6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing = {c["name"] for c in insp.get_columns("users")}
    for col, typ in [
        ("gender", sa.String(length=16)),
        ("ethnicity", sa.String(length=32)),
        ("source_school", sa.String(length=128)),
        ("grade", sa.String(length=32)),
    ]:
        if col not in existing:
            op.add_column("users", sa.Column(col, typ, nullable=False, server_default=""))


def downgrade() -> None:
    for col in ["grade", "source_school", "ethnicity", "gender"]:
        op.drop_column("users", col)
