"""drop unused legacy tables (assignments chain + grading/feedback)

Revision ID: g1h2i3j4k5l6
Revises: f9b8c7d6e5a4
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "g1h2i3j4k5l6"
down_revision: Union[str, None] = "f9b8c7d6e5a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 仅删除当前行数为 0 且已下线/被 student_case + weekly/monthly 替代的存量作业链路
    # 顺序：先删子表，再删父表，避免 FK 约束冲突
    # grading_results -> submission_answers -> submissions -> assignment_questions -> feedback_reports -> student_knowledge_records -> grading_prompt_versions -> assignments
    # 保留 questions / knowledge_points / question_knowledge_points / student_knowledge_stats（有数据或仍被 analytics 引用）
    op.drop_table("grading_results")
    op.drop_table("submission_answers")
    op.drop_table("submissions")
    op.drop_table("assignment_questions")
    op.drop_table("feedback_reports")
    op.drop_table("student_knowledge_records")
    op.drop_table("grading_prompt_versions")
    op.drop_table("assignments")


def downgrade() -> None:
    # 重建被删除的表（结构与 f8adfaa7edf4 / 86e937410e61 / 4e4d9f8a2b6c 等初始迁移保持一致）
    op.create_table(
        "assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("classes.id"), nullable=False),
        sa.Column("teacher_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(128), nullable=False),
        sa.Column("subject", sa.String(32), nullable=False),
        sa.Column("description", sa.String(512), nullable=False, server_default=""),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "grading_prompt_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("prompt_type", sa.String(32), nullable=False),
        sa.Column("prompt", sa.String(4000), nullable=False),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "student_knowledge_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("knowledge_point_id", sa.Integer(), sa.ForeignKey("knowledge_points.id"), nullable=False),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("assignment_id", sa.Integer(), sa.ForeignKey("assignments.id"), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("score", sa.Double(), nullable=True),
        sa.Column("max_score", sa.Double(), nullable=True),
        sa.Column("difficulty", sa.Double(), nullable=True),
        sa.Column("error_type", sa.String(64), nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "feedback_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("classes.id"), nullable=False),
        sa.Column("assignment_id", sa.Integer(), sa.ForeignKey("assignments.id"), nullable=False),
        sa.Column("report_type", sa.String(16), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("input_snapshot", sa.JSON(), nullable=True),
        sa.Column("ai_content", sa.Text(), nullable=True),
        sa.Column("final_content", sa.Text(), nullable=True),
        sa.Column("model_name", sa.String(64), nullable=True),
        sa.Column("prompt_version", sa.String(32), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "assignment_questions",
        sa.Column("assignment_id", sa.Integer(), sa.ForeignKey("assignments.id"), primary_key=True),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("questions.id"), primary_key=True),
        sa.Column("question_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "submissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assignment_id", sa.Integer(), sa.ForeignKey("assignments.id"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("content_type", sa.String(16), nullable=True),
        sa.Column("content_url", sa.String(512), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "submission_answers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("submission_id", sa.Integer(), sa.ForeignKey("submissions.id"), nullable=False),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("student_answer", sa.String(2000), nullable=True),
        sa.Column("ocr_text", sa.String(2000), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("score", sa.Double(), nullable=True),
        sa.Column("max_score", sa.Double(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "grading_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("submission_answer_id", sa.Integer(), sa.ForeignKey("submission_answers.id"), nullable=False),
        sa.Column("grading_type", sa.String(16), nullable=False),
        sa.Column("model_name", sa.String(64), nullable=True),
        sa.Column("ai_score", sa.Double(), nullable=True),
        sa.Column("ai_comment", sa.String(2000), nullable=True),
        sa.Column("confidence", sa.Double(), nullable=True),
        sa.Column("error_type", sa.String(64), nullable=True),
        sa.Column("error_points", sa.JSON(), nullable=True),
        sa.Column("knowledge_points", sa.JSON(), nullable=True),
        sa.Column("raw_ai_result", sa.JSON(), nullable=True),
        sa.Column("prompt_version", sa.String(32), nullable=True),
        sa.Column("teacher_score", sa.Double(), nullable=True),
        sa.Column("teacher_comment", sa.String(2000), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
