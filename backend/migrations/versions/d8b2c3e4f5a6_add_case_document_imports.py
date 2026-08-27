"""add case document imports

Revision ID: d8b2c3e4f5a6
Revises: c7a1b2d3e4f5
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d8b2c3e4f5a6"
down_revision: Union[str, None] = "c7a1b2d3e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "case_import_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("batch_key", sa.String(96), nullable=False),
        sa.Column("scope_grade", sa.String(16), nullable=False, server_default="高三"),
        sa.Column("source_root", sa.Text(), nullable=False),
        sa.Column("selected_students", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(24), nullable=False, server_default="processing"),
        sa.Column("summary", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_case_import_batches_batch_key", "case_import_batches", ["batch_key"], unique=True)
    op.create_index("ix_case_import_batches_status", "case_import_batches", ["status"])
    op.create_index("ix_case_import_batches_created_by", "case_import_batches", ["created_by"])

    op.create_table(
        "case_import_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("case_import_batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_case_id", sa.Integer(), sa.ForeignKey("student_cases.id", ondelete="SET NULL"), nullable=True),
        sa.Column("detected_student_name", sa.String(64), nullable=False),
        sa.Column("detected_subject", sa.String(32), nullable=False, server_default=""),
        sa.Column("original_path", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("file_ext", sa.String(16), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("source_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("parsed_fields", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("conflict_reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("imported_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("batch_id", "original_path", name="uq_case_import_batch_path"),
    )
    for column in ("batch_id", "student_case_id", "detected_student_name", "file_ext", "file_hash", "status"):
        op.create_index(f"ix_case_import_documents_{column}", "case_import_documents", [column])


def downgrade() -> None:
    op.drop_table("case_import_documents")
    op.drop_table("case_import_batches")
