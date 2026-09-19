"""add consultant role

Revision ID: n5o6p7q8r9s0
Revises: m4n5o6p7q8r9
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "n5o6p7q8r9s0"
down_revision: Union[str, None] = "m4n5o6p7q8r9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 咨询老师角色已在代码中定义，数据库中 users.role 字段为 String(16)，
    # 只需要确保现有数据不受影响，新角色可通过代码正常创建
    # 如果需要批量更新现有咨询老师关联的用户角色，可在此处添加
    pass


def downgrade() -> None:
    # 回滚：如果需要移除咨询老师角色，可以在此处添加
    # 但通常不需要删除角色，只需在代码中禁用即可
    pass