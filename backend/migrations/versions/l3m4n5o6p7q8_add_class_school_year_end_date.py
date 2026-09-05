"""add class school year end date

Revision ID: l3m4n5o6p7q8
Revises: k2l3m4n5o6p7
Create Date: 2026-09-02

"""

from datetime import date
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "l3m4n5o6p7q8"
down_revision: Union[str, None] = "k2l3m4n5o6p7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("classes", sa.Column("school_year_ends_on", sa.Date(), nullable=True))
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, school_year FROM classes")).mappings()
    for row in rows:
        try:
            end_year = int(str(row["school_year"]).split("-", 1)[1])
        except (TypeError, ValueError, IndexError):
            try:
                start_year = int(str(row["school_year"]).split("-", 1)[0])
            except (TypeError, ValueError):
                start_year = date.today().year
            end_year = start_year + 1
        bind.execute(
            sa.text("UPDATE classes SET school_year_ends_on = :ends_on WHERE id = :id"),
            {"ends_on": date(end_year, 7, 31), "id": row["id"]},
        )
    op.alter_column("classes", "school_year_ends_on", nullable=False)


def downgrade() -> None:
    op.drop_column("classes", "school_year_ends_on")
