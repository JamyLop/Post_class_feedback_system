"""add parent case access

Revision ID: e9c3d4e5f6a7
Revises: d8b2c3e4f5a6
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e9c3d4e5f6a7"
down_revision: Union[str, None] = "d8b2c3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "student_guardians",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relationship", sa.String(24), nullable=False, server_default="guardian"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("parent_id", "student_id", name="uq_student_guardian"),
    )
    op.create_index("ix_student_guardians_parent_id", "student_guardians", ["parent_id"])
    op.create_index("ix_student_guardians_student_id", "student_guardians", ["student_id"])


def downgrade() -> None:
    op.drop_index("ix_student_guardians_student_id", table_name="student_guardians")
    op.drop_index("ix_student_guardians_parent_id", table_name="student_guardians")
    op.drop_table("student_guardians")
