"""allow class-less student cases (consult first, enroll later)

Revision ID: b2c3d4e5f6a8
Revises: a1b2c3d4e5f7
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b2c3d4e5f6a8"
down_revision: Union[str, None] = "a1b2c3d4e5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "student_cases",
        "class_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    # 若存在无班级档案需先手动处理，否则非空约束会失败
    op.alter_column(
        "student_cases",
        "class_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
