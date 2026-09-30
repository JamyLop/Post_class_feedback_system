"""按月份管理月考成绩，保留全部历史记录与评价。"""
from alembic import op
import sqlalchemy as sa

revision = "c1d2e3f4a5b6"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("weekly_test_scores", sa.Column("exam_month", sa.String(7), nullable=True))
    # 同月多次历史周测仅最新一条进入月考统计；其余原记录及评价完整留存。
    op.execute("""
        WITH ranked AS (
            SELECT id, to_char(exam_date, 'YYYY-MM') AS month,
                   row_number() OVER (
                       PARTITION BY class_id, student_id, subject, to_char(exam_date, 'YYYY-MM')
                       ORDER BY exam_date DESC, id DESC
                   ) AS rn
            FROM weekly_test_scores
        )
        UPDATE weekly_test_scores s SET exam_month = r.month
        FROM ranked r WHERE s.id = r.id AND r.rn = 1
    """)
    op.drop_constraint("uq_weekly_score_student_subject_date", "weekly_test_scores", type_="unique")
    op.create_unique_constraint("uq_monthly_score_student_subject_month", "weekly_test_scores",
                                ["class_id", "student_id", "subject", "exam_month"])
    op.create_index("ix_weekly_test_scores_exam_month", "weekly_test_scores", ["exam_month"])


def downgrade():
    # 月考模式可修改日期，回退前检查旧约束，失败时整个事务回滚。
    op.create_unique_constraint("uq_weekly_score_student_subject_date", "weekly_test_scores",
                                ["class_id", "student_id", "subject", "exam_date"])
    op.drop_constraint("uq_monthly_score_student_subject_month", "weekly_test_scores", type_="unique")
    op.drop_index("ix_weekly_test_scores_exam_month", table_name="weekly_test_scores")
    op.drop_column("weekly_test_scores", "exam_month")
