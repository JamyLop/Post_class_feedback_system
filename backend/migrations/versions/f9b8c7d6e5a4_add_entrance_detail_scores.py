"""add entrance detail scores (total + 9 subjects)

Revision ID: f9b8c7d6e5a4
Revises: e8f9a0b1c2d3
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f9b8c7d6e5a4"
down_revision: Union[str, None] = "e8f9a0b1c2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("case_student_profiles", sa.Column("entrance_total_score", sa.Integer(), nullable=True))
    op.add_column("case_student_profiles", sa.Column("entrance_chinese", sa.Integer(), nullable=True))
    op.add_column("case_student_profiles", sa.Column("entrance_math", sa.Integer(), nullable=True))
    op.add_column("case_student_profiles", sa.Column("entrance_english", sa.Integer(), nullable=True))
    op.add_column("case_student_profiles", sa.Column("entrance_physics", sa.Integer(), nullable=True))
    op.add_column("case_student_profiles", sa.Column("entrance_chemistry", sa.Integer(), nullable=True))
    op.add_column("case_student_profiles", sa.Column("entrance_biology", sa.Integer(), nullable=True))
    op.add_column("case_student_profiles", sa.Column("entrance_politics", sa.Integer(), nullable=True))
    op.add_column("case_student_profiles", sa.Column("entrance_history", sa.Integer(), nullable=True))
    op.add_column("case_student_profiles", sa.Column("entrance_geography", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("case_student_profiles", "entrance_geography")
    op.drop_column("case_student_profiles", "entrance_history")
    op.drop_column("case_student_profiles", "entrance_politics")
    op.drop_column("case_student_profiles", "entrance_biology")
    op.drop_column("case_student_profiles", "entrance_chemistry")
    op.drop_column("case_student_profiles", "entrance_physics")
    op.drop_column("case_student_profiles", "entrance_english")
    op.drop_column("case_student_profiles", "entrance_math")
    op.drop_column("case_student_profiles", "entrance_chinese")
    op.drop_column("case_student_profiles", "entrance_total_score")
