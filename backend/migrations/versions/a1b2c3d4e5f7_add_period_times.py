"""add period times

Revision ID: a1b2c3d4e5f7
Revises: z6a7b8c9d0e1
"""

from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f7"
down_revision = "z6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "period_times",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("period", sa.Integer(), nullable=False, unique=True),
        sa.Column("start_time", sa.String(5), nullable=False),
        sa.Column("end_time", sa.String(5), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_period_times_period", "period_times", ["period"])

    # 插入默认的12个节次时间
    period_table = sa.table(
        "period_times",
        sa.Column("period", sa.Integer()),
        sa.Column("start_time", sa.String()),
        sa.Column("end_time", sa.String()),
    )
    op.bulk_insert(
        period_table,
        [
            {"period": 1, "start_time": "08:00", "end_time": "08:45"},
            {"period": 2, "start_time": "08:55", "end_time": "09:40"},
            {"period": 3, "start_time": "10:00", "end_time": "10:45"},
            {"period": 4, "start_time": "10:55", "end_time": "11:40"},
            {"period": 5, "start_time": "14:00", "end_time": "14:45"},
            {"period": 6, "start_time": "14:55", "end_time": "15:40"},
            {"period": 7, "start_time": "16:00", "end_time": "16:45"},
            {"period": 8, "start_time": "16:55", "end_time": "17:40"},
            {"period": 9, "start_time": "19:00", "end_time": "19:45"},
            {"period": 10, "start_time": "19:55", "end_time": "20:40"},
            {"period": 11, "start_time": "20:50", "end_time": "21:35"},
            {"period": 12, "start_time": "21:45", "end_time": "22:30"},
        ],
    )


def downgrade() -> None:
    op.drop_table("period_times")
