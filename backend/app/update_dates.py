"""将数据库中所有日期更新为 2026-08-19。

用法：python -m app.update_dates
"""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import text

from app.core.database import engine

TZ_UTC8 = timezone(timedelta(hours=8))
TARGET = datetime(2026, 8, 19, 10, 0, 0, tzinfo=TZ_UTC8)
TARGET_DATE = date(2026, 8, 19)


def update_dates() -> None:
    with engine.begin() as conn:
        # assignments.due_at
        conn.execute(text("UPDATE assignments SET due_at = :t"), {"t": TARGET + timedelta(days=7)})
        # assignments.created_at / updated_at
        conn.execute(text("UPDATE assignments SET created_at = :t, updated_at = :t"), {"t": TARGET})

        # submissions.submitted_at / updated_at
        conn.execute(text("UPDATE submissions SET submitted_at = :t, updated_at = :t"), {"t": TARGET})

        # submission_answers.created_at / updated_at
        conn.execute(text("UPDATE submission_answers SET created_at = :t, updated_at = :t"), {"t": TARGET})

        # grading_results.created_at / reviewed_at
        conn.execute(text("UPDATE grading_results SET created_at = :t, reviewed_at = :t"), {"t": TARGET})

        # feedback_reports.period_start / period_end / generated_at / published_at / created_at / updated_at
        conn.execute(text(
            "UPDATE feedback_reports SET period_start = :ds, period_end = :de, "
            "generated_at = :t, published_at = :t, created_at = :t, updated_at = :t"
        ), {"ds": TARGET_DATE - timedelta(days=7), "de": TARGET_DATE, "t": TARGET})

        # knowledge_points.created_at
        conn.execute(text("UPDATE knowledge_points SET created_at = :t"), {"t": TARGET})
        # student_knowledge_records.answered_at / created_at
        conn.execute(text("UPDATE student_knowledge_records SET answered_at = :t, created_at = :t"), {"t": TARGET})
        # student_knowledge_stats.last_updated
        conn.execute(text("UPDATE student_knowledge_stats SET last_updated = :t"), {"t": TARGET})

        # invite_codes — 保留 expires_at 不动，只改 created_at
        conn.execute(text("UPDATE invite_codes SET created_at = :t, updated_at = :t"), {"t": TARGET})

        # class_students.joined_at
        conn.execute(text("UPDATE class_students SET joined_at = :t"), {"t": TARGET})

    print("所有日期已更新为 2026-08-19。")


if __name__ == "__main__":
    update_dates()
