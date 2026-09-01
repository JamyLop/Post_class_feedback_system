"""require weekly score max score from recorder

Revision ID: j1k2l3m4n5o6
Revises: j0k1l2m3n4o5
Create Date: 2026-09-01

"""

from typing import Sequence, Union

from alembic import op

revision: str = "j1k2l3m4n5o6"
down_revision: Union[str, None] = "j0k1l2m3n4o5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 保留历史记录中的满分，只取消数据库自动补 100 的行为。
    op.alter_column("weekly_test_scores", "max_score", server_default=None)


def downgrade() -> None:
    op.alter_column("weekly_test_scores", "max_score", server_default="100")
