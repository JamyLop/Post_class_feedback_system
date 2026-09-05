"""add class school year start date

Revision ID: j0k1l2m3n4o5
Revises: i9j0k1l2m3n4
Create Date: 2026-09-01

"""

from datetime import date
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "j0k1l2m3n4o5"
down_revision: Union[str, None] = "i9j0k1l2m3n4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("classes", sa.Column("school_year_starts_on", sa.Date(), nullable=True))
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, school_year FROM classes")).mappings()
    for row in rows:
        try:
            start_year = int(str(row["school_year"]).split("-", 1)[0])
        except (TypeError, ValueError):
            start_year = date.today().year
        bind.execute(
            sa.text("UPDATE classes SET school_year_starts_on = :starts_on WHERE id = :id"),
            {"starts_on": date(start_year, 8, 1), "id": row["id"]},
        )
    op.alter_column("classes", "school_year_starts_on", nullable=False)


def downgrade() -> None:
    op.drop_column("classes", "school_year_starts_on")
