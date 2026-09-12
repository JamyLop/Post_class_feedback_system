"""task daily-1-point + weekly-times

Revision ID: v2w3x4y5z6a7
Revises: u1v2w3x4y5z6
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "v2w3x4y5z6a7"
down_revision: Union[str, None] = "u1v2w3x4y5z6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("case_tasks", sa.Column("weekly_times", sa.Integer(), nullable=True))
    # 历史任务 points 统一收敛为 1（每天每任务满分 1 分），周报按单科每周封顶 7 分重算。
    op.execute("UPDATE case_tasks SET points = 1")
    # 历史打卡按新口径回填：earned = completion_rate / 100（满分 1 分），避免旧权重残留。
    op.execute("UPDATE task_checkins SET earned_points = ROUND(completion_rate / 100.0, 2)")
    # 历史周任务没有执行次数，默认回填 1（班主任可在前端按实际调整），避免详情接口校验失败。
    op.execute("UPDATE case_tasks SET weekly_times = 1 WHERE cadence = 'weekly' AND weekly_times IS NULL")


def downgrade() -> None:
    op.drop_column("case_tasks", "weekly_times")
