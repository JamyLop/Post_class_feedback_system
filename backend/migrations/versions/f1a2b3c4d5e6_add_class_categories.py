"""add class categories

Revision ID: f1a2b3c4d5e6
Revises: a2c3d4e5f6a7
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "a2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "classes",
        sa.Column("education_stage", sa.String(16), nullable=False, server_default="高中"),
    )
    op.add_column(
        "classes",
        sa.Column("class_type", sa.String(16), nullable=False, server_default="全年班"),
    )
    op.add_column("classes", sa.Column("short_term_type", sa.String(16), nullable=True))
    # 存量年级按中文名称回填学段，其余历史数据保持高中兼容值，待业务侧确认。
    op.execute(
        "UPDATE classes SET education_stage = '初中' "
        "WHERE grade LIKE '初%%' OR grade IN ('七年级', '八年级', '九年级')"
    )
    op.execute("UPDATE classes SET grade = '初一' WHERE grade = '七年级'")
    op.execute("UPDATE classes SET grade = '初二' WHERE grade = '八年级'")
    op.execute("UPDATE classes SET grade = '初三' WHERE grade = '九年级'")


def downgrade() -> None:
    op.drop_column("classes", "short_term_type")
    op.drop_column("classes", "class_type")
    op.drop_column("classes", "education_stage")
