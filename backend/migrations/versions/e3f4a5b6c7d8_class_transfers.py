"""批量调班审计与考试选科快照。

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
"""
from alembic import op
import sqlalchemy as sa

revision = "e3f4a5b6c7d8"
down_revision = "d2e3f4a5b6c7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("class_transfer_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.String(64), nullable=False, unique=True),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("actor_name", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_class_transfer_batches_created_at", "class_transfer_batches", ["created_at"])
    op.create_table("class_transfer_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("class_transfer_batches.id"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("student_username", sa.String(64), nullable=False),
        sa.Column("student_name", sa.String(64), nullable=False),
        sa.Column("source_class_id", sa.Integer(), sa.ForeignKey("classes.id"), nullable=False),
        sa.Column("target_class_id", sa.Integer(), sa.ForeignKey("classes.id"), nullable=False),
        sa.Column("source_class_name", sa.String(64), nullable=False),
        sa.Column("target_class_name", sa.String(64), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=False))
    for column in ("batch_id", "student_id", "source_class_id", "target_class_id", "effective_at"):
        op.create_index(f"ix_class_transfer_items_{column}", "class_transfer_items", [column])
    op.add_column("weekly_test_scores", sa.Column("study_subjects_snapshot", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("weekly_test_scores", "study_subjects_snapshot")
    op.drop_table("class_transfer_items")
    op.drop_table("class_transfer_batches")
