"""阶段 5：学情分析 —— 掌握度聚合服务。

数据流：student_knowledge_records（原始轨迹，教师确认时写入）
       → 重算 student_knowledge_stats（聚合表，确认时增量更新）
       → 学情 API 直接读聚合表。

第一版掌握度公式：correct_count / (correct_count + wrong_count)。
"""

from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models import Submission
from app.models.assignment import (
    ASSIGNMENT_STATUS_CLOSED,
    ASSIGNMENT_STATUS_PUBLISHED,
    Assignment,
)
from app.models.grading import GRADING_STATUS_CONFIRMED, GradingResult
from app.models.knowledge import KnowledgePoint, StudentKnowledgeRecord, StudentKnowledgeStat
from app.models.question import Question, QuestionKnowledgePoint
from app.models.submission import (
    SUBMISSION_STATUS_TEACHER_REVIEWED,
    Submission,
    SubmissionAnswer,
)
from app.models.user import User

TREND_NEW = "new"
TREND_UP = "up"
TREND_DOWN = "down"
TREND_STABLE = "stable"

# 趋势判定阈值：最近半段正确率与前半段之差
TREND_THRESHOLD = 0.1

# 成绩分布区间（按百分比）
DIST_BUCKETS = ["ge90", "ge80", "ge70", "ge60", "lt60"]
DIST_LABELS = {
    "ge90": "90分以上",
    "ge80": "80~89",
    "ge70": "70~79",
    "ge60": "60~69",
    "lt60": "60分以下",
}


def _compute_trend(records: list[StudentKnowledgeRecord]) -> str:
    """按作业聚合正确率，再比较前后两个时间阶段。"""
    # 按作业分组，只统计有判定结果的记录
    assignments: dict[int, list[StudentKnowledgeRecord]] = {}
    for record in records:
        if record.is_correct is not None:
            assignments.setdefault(record.assignment_id, []).append(record)
    if len(assignments) < 2:
        # 不足两个作业无法判断趋势
        return TREND_NEW

    rates = []
    for assignment_records in assignments.values():
        ordered = sorted(
            assignment_records,
            key=lambda r: (r.answered_at, r.assignment_id, r.id or 0),
        )
        rates.append(
            (
                ordered[0].answered_at,
                ordered[0].assignment_id,
                sum(1 for r in ordered if r.is_correct is True) / len(ordered),
            )
        )
    rates.sort(key=lambda item: (item[0], item[1]))
    mid = len(rates) // 2
    first = rates[:mid]
    last = rates[mid:]
    fa = sum(item[2] for item in first) / len(first)
    la = sum(item[2] for item in last) / len(last)
    diff = la - fa
    if diff > TREND_THRESHOLD:
        return TREND_UP
    if diff < -TREND_THRESHOLD:
        return TREND_DOWN
    return TREND_STABLE


def recompute_student_stats(
    db: Session,
    student_id: int,
    kp_ids: list[int] | None = None,
) -> None:
    """按原始轨迹重算某学生的知识点聚合（默认全部；可指定知识点）。不提交事务。"""
    if kp_ids is None:
        # 全量重算：合并轨迹中与聚合表中出现的所有知识点
        record_kp_ids = {
            r[0]
            for r in db.query(StudentKnowledgeRecord.knowledge_point_id)
            .filter(StudentKnowledgeRecord.student_id == student_id)
            .distinct()
            .all()
        }
        stat_kp_ids = {
            r[0]
            for r in db.query(StudentKnowledgeStat.knowledge_point_id)
            .filter(StudentKnowledgeStat.student_id == student_id)
            .all()
        }
        kp_ids = list(record_kp_ids | stat_kp_ids)
    for kp_id in set(kp_ids):
        records = (
            db.query(StudentKnowledgeRecord)
            .filter(
                StudentKnowledgeRecord.student_id == student_id,
                StudentKnowledgeRecord.knowledge_point_id == kp_id,
            )
            .order_by(
                StudentKnowledgeRecord.answered_at.asc(),
                StudentKnowledgeRecord.assignment_id.asc(),
                StudentKnowledgeRecord.id.asc(),
            )
            .all()
        )
        if not records:
            # 该知识点无轨迹但存在聚合行：删除残留聚合
            stat = (
                db.query(StudentKnowledgeStat)
                .filter(
                    StudentKnowledgeStat.student_id == student_id,
                    StudentKnowledgeStat.knowledge_point_id == kp_id,
                )
                .first()
            )
            if stat is not None:
                db.delete(stat)
            continue
        correct = sum(1 for r in records if r.is_correct is True)
        wrong = sum(1 for r in records if r.is_correct is False)
        total = correct + wrong
        mastery = round(correct / total, 4) if total else 0.0
        # PostgreSQL upsert：并发重算同一 (student, kp) 时不会唯一键冲突
        insert_stmt = pg_insert(StudentKnowledgeStat).values(
            student_id=student_id,
            knowledge_point_id=kp_id,
            correct_count=correct,
            wrong_count=wrong,
            mastery_score=mastery,
            trend=_compute_trend(records),
            last_updated=datetime.now(timezone.utc),
        )
        stmt = insert_stmt.on_conflict_do_update(
            constraint="student_knowledge_stats_student_id_knowledge_point_id_key",
            set_={
                "correct_count": insert_stmt.excluded.correct_count,
                "wrong_count": insert_stmt.excluded.wrong_count,
                "mastery_score": insert_stmt.excluded.mastery_score,
                "trend": insert_stmt.excluded.trend,
                "last_updated": insert_stmt.excluded.last_updated,
            },
        )
        db.execute(stmt)


def ensure_student_stats(db: Session, student_id: int) -> None:
    """读接口兜底：学生有轨迹但没有聚合行（如旧数据/直接造数据）时先全量重算。"""
    record_kp_ids = {
        row[0]
        for row in db.query(StudentKnowledgeRecord.knowledge_point_id)
        .filter(StudentKnowledgeRecord.student_id == student_id)
        .distinct()
        .all()
    }
    stat_kp_ids = {
        row[0]
        for row in db.query(StudentKnowledgeStat.knowledge_point_id)
        .filter(StudentKnowledgeStat.student_id == student_id)
        .all()
    }
    if record_kp_ids != stat_kp_ids:
        recompute_student_stats(db, student_id)
        db.commit()


def _stat_rows(db: Session, student_id: int, kp_ids: list[int] | None = None):
    """查询学生的聚合行并 join 知识点信息（可限定知识点）。"""
    q = (
        db.query(StudentKnowledgeStat, KnowledgePoint)
        .join(
            KnowledgePoint,
            KnowledgePoint.id == StudentKnowledgeStat.knowledge_point_id,
        )
        .filter(StudentKnowledgeStat.student_id == student_id)
    )
    if kp_ids:
        q = q.filter(StudentKnowledgeStat.knowledge_point_id.in_(kp_ids))
    return q.all()


def _scoped_student_stats(db: Session, student_id: int, class_id: int):
    """按班级范围重算知识点掌握度（直接从轨迹聚合，不入聚合表）。"""
    records = (
        db.query(StudentKnowledgeRecord)
        .join(Assignment, Assignment.id == StudentKnowledgeRecord.assignment_id)
        .filter(
            StudentKnowledgeRecord.student_id == student_id,
            Assignment.class_id == class_id,
        )
        .order_by(
            StudentKnowledgeRecord.answered_at.asc(),
            StudentKnowledgeRecord.assignment_id.asc(),
            StudentKnowledgeRecord.id.asc(),
        )
        .all()
    )
    grouped: dict[int, list[StudentKnowledgeRecord]] = {}
    for record in records:
        grouped.setdefault(record.knowledge_point_id, []).append(record)
    points = {
        point.id: point
        for point in db.query(KnowledgePoint)
        .filter(KnowledgePoint.id.in_(list(grouped) or [0]))
        .all()
    }
    rows = []
    for kp_id, kp_records in grouped.items():
        correct = sum(1 for record in kp_records if record.is_correct is True)
        wrong = sum(1 for record in kp_records if record.is_correct is False)
        total = correct + wrong
        point = points.get(kp_id)
        rows.append(
            {
                "knowledge_point_id": kp_id,
                "name": point.name if point else f"kp_{kp_id}",
                "code": point.code if point else "",
                "chapter": point.chapter if point else "",
                "correct_count": correct,
                "wrong_count": wrong,
                "mastery_score": round(correct / total, 4) if total else 0.0,
                "trend": _compute_trend(kp_records),
                "last_updated": max(record.created_at for record in kp_records),
            }
        )
    rows.sort(key=lambda row: (row["mastery_score"], row["knowledge_point_id"]))
    return rows


def get_student_knowledge_stats(
    db: Session,
    student_id: int,
    class_id: int | None = None,
):
    """学生知识点掌握度列表（掌握度升序）。"""
    if class_id is not None:
        return _scoped_student_stats(db, student_id, class_id)
    rows = _stat_rows(db, student_id)
    result = [
        {
            "knowledge_point_id": kp.id,
            "name": kp.name,
            "code": kp.code,
            "chapter": kp.chapter,
            "correct_count": s.correct_count,
            "wrong_count": s.wrong_count,
            "mastery_score": s.mastery_score,
            "trend": s.trend,
            "last_updated": s.last_updated,
        }
        for s, kp in rows
    ]
    result.sort(key=lambda row: (row["mastery_score"], row["knowledge_point_id"]))
    return result


def get_student_weak_points(
    db: Session,
    student_id: int,
    top_n: int = 5,
    min_records: int = 1,
    class_id: int | None = None,
):
    """薄弱知识点 TOP N：掌握度升序，优先展示做题数多的薄弱点。"""
    if class_id is not None:
        rows = _scoped_student_stats(db, student_id, class_id)
        rows = [
            row
            for row in rows
            if (row["correct_count"] + row["wrong_count"]) >= min_records
        ]
        rows.sort(
            key=lambda row: (
                row["mastery_score"],
                -(row["correct_count"] + row["wrong_count"]),
            )
        )
        return [
            {key: value for key, value in row.items() if key != "last_updated"}
            for row in rows[:top_n]
        ]
    rows = _stat_rows(db, student_id)
    rows = [
        (s, kp)
        for s, kp in rows
        if (s.correct_count + s.wrong_count) >= min_records
    ]
    rows.sort(
        key=lambda item: (item[0].mastery_score, -(item[0].correct_count + item[0].wrong_count))
    )
    return [
        {
            "knowledge_point_id": kp.id,
            "name": kp.name,
            "code": kp.code,
            "chapter": kp.chapter,
            "correct_count": s.correct_count,
            "wrong_count": s.wrong_count,
            "mastery_score": s.mastery_score,
            "trend": s.trend,
        }
        for s, kp in rows[:top_n]
    ]


def get_student_learning_trend(
    db: Session,
    student_id: int,
    class_id: int | None = None,
):
    """学生成绩趋势：按提交时间排序的已确认作业得分百分比。"""
    query = db.query(Submission).filter(
        Submission.student_id == student_id,
        Submission.status == SUBMISSION_STATUS_TEACHER_REVIEWED,
    )
    if class_id is not None:
        query = query.join(Assignment, Assignment.id == Submission.assignment_id).filter(
            Assignment.class_id == class_id
        )
    subs = query.order_by(Submission.submitted_at.asc(), Submission.id.asc()).all()
    points = []
    for sub in subs:
        answers = (
            db.query(SubmissionAnswer)
            .filter(SubmissionAnswer.submission_id == sub.id)
            .all()
        )
        total = sum(a.score or 0 for a in answers)
        max_total = sum(a.max_score or 0 for a in answers)
        percent = round(total / max_total * 100, 1) if max_total else 0.0
        points.append(
            {
                "assignment_id": sub.assignment_id,
                "submission_id": sub.id,
                "total_score": round(total, 1),
                "max_total": round(max_total, 1),
                "percent": percent,
                "submitted_at": sub.submitted_at,
            }
        )
    return {"points": points}


def get_student_repeated_errors(
    db: Session,
    student_id: int,
    top_n: int = 10,
    min_count: int = 2,
    class_id: int | None = None,
):
    """学生重复错误：按已确认批改的错误类型聚合。"""
    query = (
        db.query(GradingResult.error_type)
        .join(SubmissionAnswer, SubmissionAnswer.id == GradingResult.submission_answer_id)
        .join(Submission, Submission.id == SubmissionAnswer.submission_id)
        .filter(
            Submission.student_id == student_id,
            Submission.status == SUBMISSION_STATUS_TEACHER_REVIEWED,
            GradingResult.status == GRADING_STATUS_CONFIRMED,
            GradingResult.error_type.isnot(None),
        )
    )
    if class_id is not None:
        query = query.join(Assignment, Assignment.id == Submission.assignment_id).filter(
            Assignment.class_id == class_id
        )
    counts: dict[str, int] = {}
    for (error_type,) in query.all():
        if error_type:
            counts[error_type] = counts.get(error_type, 0) + 1
    rows = [
        {"error_type": error_type, "count": count}
        for error_type, count in counts.items()
        if count >= min_count
    ]
    rows.sort(key=lambda row: (-row["count"], row["error_type"]))
    return rows[:top_n]


def _score_percent(total: float, max_total: float) -> float:
    """得分百分比（满分 0 时返回 0）。"""
    return round(total / max_total * 100, 1) if max_total else 0.0


def _bucket(percent: float) -> str:
    """按百分比映射到成绩分布区间。"""
    if percent >= 90:
        return "ge90"
    if percent >= 80:
        return "ge80"
    if percent >= 70:
        return "ge70"
    if percent >= 60:
        return "ge60"
    return "lt60"


def _empty_distribution() -> dict:
    """全零成绩分布。"""
    return {k: 0 for k in DIST_BUCKETS}


def _confirmed_submissions(db: Session, assignment_id: int) -> list[type[Submission]]:
    """某作业下所有已确认的提交。"""
    return (
        db.query(Submission)
        .filter(
            Submission.assignment_id == assignment_id,
            Submission.status == SUBMISSION_STATUS_TEACHER_REVIEWED,
        )
        .all()
    )


def get_assignment_analysis(db: Session, assignment_id: int):
    """单次作业分析：平均分/分布/各题正确率/薄弱知识点/共性错误。"""
    subs = _confirmed_submissions(db, assignment_id)

    percents = [_score_percent(_sub_total(db, s), _sub_max(db, s)) for s in subs]
    distribution = _empty_distribution()
    for p in percents:
        distribution[_bucket(p)] += 1
    avg_score = round(sum(percents) / len(percents), 1) if percents else 0.0
    pass_rate = round(sum(1 for p in percents if p >= 60) / len(percents), 4) if percents else 0.0

    # 各题正确率
    question_stats: dict[int, dict] = {}
    answer_rows = (
        db.query(SubmissionAnswer, Question)
        .join(Question, Question.id == SubmissionAnswer.question_id)
        .filter(SubmissionAnswer.submission_id.in_([s.id for s in subs]))
        .all()
    )
    for answer, question in answer_rows:
        st = question_stats.setdefault(
            question.id,
            {
                "question_id": question.id,
                "question_type": question.question_type,
                "content": question.content,
                "max_score": answer.max_score or question.score or 0,
                "correct_count": 0,
                "gradable_count": 0,
                "count": 0,
            },
        )
        if answer.is_correct is not None:
            st["gradable_count"] += 1
            if answer.is_correct:
                st["correct_count"] += 1
        st["count"] += 1
    questions_out = []
    for st in question_stats.values():
        accuracy = (
            round(st["correct_count"] / st["gradable_count"], 4)
            if st["gradable_count"]
            else 0.0
        )
        questions_out.append(
            {
                "question_id": st["question_id"],
                "question_type": st["question_type"],
                "content": st["content"],
                "max_score": round(st["max_score"], 1),
                "accuracy": accuracy,
                "answer_count": st["count"],
            }
        )
    questions_out.sort(key=lambda q: q["accuracy"])

    # 薄弱知识点（来自本作业的确认记录）
    weak = get_assignment_weak_points(db, assignment_id, top_n=10)

    # 共性错误（确认后的错误类型分布）
    error_types = _assignment_error_types(db, assignment_id)

    return {
        "assignment_id": assignment_id,
        "submission_count": len(subs),
        "average_score": avg_score,
        "pass_rate": pass_rate,
        "score_distribution": distribution,
        "question_accuracy": questions_out,
        "weak_knowledge_points": weak,
        "common_errors": error_types,
    }


def _sub_total(db: Session, sub: Submission) -> float:
    """某提交各题得分之和。"""
    answers = db.query(SubmissionAnswer).filter(SubmissionAnswer.submission_id == sub.id).all()
    return sum(a.score or 0 for a in answers)


def _sub_max(db: Session, sub: Submission) -> float:
    """某提交各题满分之和。"""
    answers = db.query(SubmissionAnswer).filter(SubmissionAnswer.submission_id == sub.id).all()
    return sum(a.max_score or 0 for a in answers)


def get_assignment_weak_points(
    db: Session,
    assignment_id: int,
    top_n: int = 5,
):
    """作业级薄弱知识点：基于该作业全部确认记录，按正确率升序。"""
    kp_acc: dict[int, dict] = {}
    records = (
        db.query(StudentKnowledgeRecord)
        .filter(StudentKnowledgeRecord.assignment_id == assignment_id)
        .all()
    )
    for rec in records:
        if rec.is_correct is None:
            continue
        st = kp_acc.setdefault(
            rec.knowledge_point_id, {"correct": 0, "wrong": 0}
        )
        if rec.is_correct:
            st["correct"] += 1
        else:
            st["wrong"] += 1
    kp_names = {
        kp.id: kp
        for kp in db.query(KnowledgePoint)
        .filter(KnowledgePoint.id.in_(list(kp_acc.keys()) or [0]))
        .all()
    }
    rows = []
    for kp_id, st in kp_acc.items():
        total = st["correct"] + st["wrong"]
        accuracy = round(st["correct"] / total, 4) if total else 0.0
        kp = kp_names.get(kp_id)
        rows.append(
            {
                "knowledge_point_id": kp_id,
                "name": kp.name if kp else f"kp_{kp_id}",
                "code": kp.code if kp else "",
                "chapter": kp.chapter if kp else "",
                "correct_count": st["correct"],
                "wrong_count": st["wrong"],
                "mastery_score": accuracy,
            }
        )
    rows.sort(key=lambda r: r["mastery_score"])
    return rows[:top_n]


def _assignment_error_types(db: Session, assignment_id: int):
    """作业共性错误：已确认批改的错误类型分布。"""
    counts: dict[str, int] = {}
    rows = (
        db.query(GradingResult.error_type)
        .join(SubmissionAnswer, SubmissionAnswer.id == GradingResult.submission_answer_id)
        .join(Submission, Submission.id == SubmissionAnswer.submission_id)
        .filter(
            Submission.assignment_id == assignment_id,
            GradingResult.status == GRADING_STATUS_CONFIRMED,
            GradingResult.error_type.isnot(None),
        )
        .all()
    )
    for (error_type,) in rows:
        counts[error_type] = counts.get(error_type, 0) + 1
    out = [{"error_type": k, "count": v} for k, v in counts.items()]
    out.sort(key=lambda x: x["count"], reverse=True)
    return out


def get_class_analytics(db: Session, class_id: int, student_ids: list[int]):
    """班级学情：平均分/成绩分布/知识点正确率/薄弱排行/共性错误/未提交学生。"""
    subs = (
        db.query(Submission)
        .join(Assignment, Assignment.id == Submission.assignment_id)
        .filter(
            Submission.student_id.in_(student_ids or [0]),
            Submission.status == SUBMISSION_STATUS_TEACHER_REVIEWED,
            Assignment.class_id == class_id,
        )
        .all()
    )

    percents = [_score_percent(_sub_total(db, s), _sub_max(db, s)) for s in subs]
    distribution = _empty_distribution()
    for p in percents:
        distribution[_bucket(p)] += 1
    avg_score = round(sum(percents) / len(percents), 1) if percents else 0.0

    # 班级知识点整体正确率（聚合所有学生的确认记录）
    kp_acc: dict[int, dict] = {}
    records = (
        db.query(StudentKnowledgeRecord)
        .join(Assignment, Assignment.id == StudentKnowledgeRecord.assignment_id)
        .filter(
            StudentKnowledgeRecord.student_id.in_(student_ids or [0]),
            Assignment.class_id == class_id,
        )
        .all()
    )
    for rec in records:
        if rec.is_correct is None:
            continue
        st = kp_acc.setdefault(rec.knowledge_point_id, {"correct": 0, "wrong": 0})
        if rec.is_correct:
            st["correct"] += 1
        else:
            st["wrong"] += 1
    kp_names = {
        kp.id: kp
        for kp in db.query(KnowledgePoint)
        .filter(KnowledgePoint.id.in_(list(kp_acc.keys()) or [0]))
        .all()
    }
    knowledge_rows = []
    for kp_id, st in kp_acc.items():
        total = st["correct"] + st["wrong"]
        accuracy = round(st["correct"] / total, 4) if total else 0.0
        kp = kp_names.get(kp_id)
        knowledge_rows.append(
            {
                "knowledge_point_id": kp_id,
                "name": kp.name if kp else f"kp_{kp_id}",
                "code": kp.code if kp else "",
                "chapter": kp.chapter if kp else "",
                "correct_count": st["correct"],
                "wrong_count": st["wrong"],
                "mastery_score": accuracy,
            }
        )
    knowledge_rows.sort(key=lambda r: r["mastery_score"])
    weak_points = knowledge_rows[:10]

    # 共性错误（班级全部已确认批改）
    error_counts: dict[str, int] = {}
    error_rows = (
        db.query(GradingResult.error_type)
        .join(SubmissionAnswer, SubmissionAnswer.id == GradingResult.submission_answer_id)
        .join(Submission, Submission.id == SubmissionAnswer.submission_id)
        .join(Assignment, Assignment.id == Submission.assignment_id)
        .filter(
            Submission.student_id.in_(student_ids or [0]),
            Submission.status == SUBMISSION_STATUS_TEACHER_REVIEWED,
            Assignment.class_id == class_id,
            GradingResult.status == GRADING_STATUS_CONFIRMED,
            GradingResult.error_type.isnot(None),
        )
        .all()
    )
    for (error_type,) in error_rows:
        error_counts[error_type] = error_counts.get(error_type, 0) + 1
    common_errors = [
        {"error_type": k, "count": v} for k, v in error_counts.items()
    ]
    common_errors.sort(key=lambda x: x["count"], reverse=True)

    # 未提交学生：相对班级最近一次作业（已发布或已关闭）
    unsubmitted = _unsubmitted_students(db, class_id, student_ids)

    return {
        "class_id": class_id,
        "submission_count": len(subs),
        "average_score": avg_score,
        "score_distribution": distribution,
        "knowledge_accuracy": knowledge_rows,
        "weak_knowledge_points": weak_points,
        "common_errors": common_errors,
        "unsubmitted_students": unsubmitted,
    }


def _unsubmitted_students(
    db: Session,
    class_id: int,
    student_ids: list[int],
):
    """未提交学生：当前班级最近一次已发布/已关闭作业没有提交记录的学生。"""
    latest_assignment = (
        db.query(Assignment.id)
        .filter(
            Assignment.class_id == class_id,
            Assignment.status.in_([ASSIGNMENT_STATUS_PUBLISHED, ASSIGNMENT_STATUS_CLOSED]),
        )
        .order_by(Assignment.created_at.desc(), Assignment.id.desc())
        .first()
    )
    if latest_assignment is None:
        return []
    latest_aid = latest_assignment[0]
    submitted_ids = {
        r[0]
        for r in db.query(Submission.student_id)
        .filter(
            Submission.assignment_id == latest_aid,
        )
        .all()
    }
    rows = (
        db.query(User)
        .filter(User.id.in_(student_ids or [0]), User.id.notin_(submitted_ids or [0]))
        .all()
    )
    return [
        {"student_id": u.id, "name": u.name} for u in sorted(rows, key=lambda u: u.id)
    ]
