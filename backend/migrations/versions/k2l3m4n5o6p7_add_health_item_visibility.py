"""Add per-item visibility switches for health profile fields.

Revision ID: k2l3m4n5o6p7
Revises: j1k2l3m4n5o6
"""

from alembic import op
import sqlalchemy as sa


revision = "k2l3m4n5o6p7"
down_revision = "j1k2l3m4n5o6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("case_student_profiles", sa.Column("allergy_visible", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("case_student_profiles", sa.Column("underlying_conditions_visible", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("case_student_profiles", sa.Column("other_health_notes_visible", sa.Boolean(), nullable=False, server_default=sa.true()))
    # 历史档案已有整体开关：关闭整体开关的记录继续保持三个单项均不可见。
    op.execute(sa.text("""
        UPDATE case_student_profiles
        SET allergy_visible = health_visible,
            underlying_conditions_visible = health_visible,
            other_health_notes_visible = health_visible
    """))


def downgrade() -> None:
    op.drop_column("case_student_profiles", "other_health_notes_visible")
    op.drop_column("case_student_profiles", "underlying_conditions_visible")
    op.drop_column("case_student_profiles", "allergy_visible")
