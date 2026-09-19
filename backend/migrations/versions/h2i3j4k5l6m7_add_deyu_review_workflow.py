"""add deyu review workflow

Revision ID: h2i3j4k5l6m7
Revises: g1h2i3j4k5l6
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "h2i3j4k5l6m7"
down_revision: Union[str, None] = "g1h2i3j4k5l6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("case_reviews", sa.Column("decision", sa.String(24), nullable=False, server_default=""))
    op.add_column("case_reviews", sa.Column("workflow_status", sa.String(24), nullable=False, server_default="closed"))
    op.add_column("case_reviews", sa.Column("target_version", sa.Integer(), nullable=True))
    op.add_column("case_reviews", sa.Column("assigned_to", sa.Integer(), nullable=True))
    op.add_column("case_reviews", sa.Column("visibility", sa.String(16), nullable=False, server_default="shared"))
    op.add_column("case_reviews", sa.Column("resubmitted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("case_reviews", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key("fk_case_reviews_assigned_to_users", "case_reviews", "users", ["assigned_to"], ["id"])
    op.create_index("ix_case_reviews_decision", "case_reviews", ["decision"])
    op.create_index("ix_case_reviews_workflow_status", "case_reviews", ["workflow_status"])
    op.create_index("ix_case_reviews_assigned_to", "case_reviews", ["assigned_to"])
    op.create_index("ix_case_reviews_visibility", "case_reviews", ["visibility"])


def downgrade() -> None:
    op.drop_index("ix_case_reviews_visibility", table_name="case_reviews")
    op.drop_index("ix_case_reviews_assigned_to", table_name="case_reviews")
    op.drop_index("ix_case_reviews_workflow_status", table_name="case_reviews")
    op.drop_index("ix_case_reviews_decision", table_name="case_reviews")
    op.drop_constraint("fk_case_reviews_assigned_to_users", "case_reviews", type_="foreignkey")
    op.drop_column("case_reviews", "resolved_at")
    op.drop_column("case_reviews", "resubmitted_at")
    op.drop_column("case_reviews", "visibility")
    op.drop_column("case_reviews", "assigned_to")
    op.drop_column("case_reviews", "target_version")
    op.drop_column("case_reviews", "workflow_status")
    op.drop_column("case_reviews", "decision")
