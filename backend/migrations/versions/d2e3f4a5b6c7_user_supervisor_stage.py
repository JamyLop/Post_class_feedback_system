"""任课老师附加学段主管身份。

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
"""
from alembic import op
import sqlalchemy as sa

revision = "d2e3f4a5b6c7"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("supervisor_stage", sa.String(16), nullable=False, server_default=""))


def downgrade():
    op.drop_column("users", "supervisor_stage")
