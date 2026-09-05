"""阶段完成度重算与积分周报/月报累加逻辑。"""

import calendar
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.case_points import CaseStageCompletion, StudentPointsReport
from app.models.class_ import Class, ClassStudent
from app.models.student_case import CaseTask, StudentCase, TaskCheckin
from app.models.user import User


def _latest_checkins_by_task(db: Session, task_ids: list[int]) -> dict[int, TaskCheckin]:
    """每个任务取最新一条打卡（checked_in_at 倒序首条）。"""
    latest: dict[int, TaskCheckin] = {}
    if not task_ids:
        return latest
    rows = (
        db.query(TaskCheckin)
        .filter(TaskCheckin.task_id.in_(task_ids))
        .order_by(TaskCheckin.checked_in_at.desc(), TaskCheckin.id.desc())
        .all()
    )
    for row in rows:
        if row.task_id not in latest:
            latest[row.task_id] = row
    return latest


def earned_of(task_points: int, rate: int) -> float:
    return round((task_points or 0) * (rate or 0) / 100.0, 2)


def recompute_stage_completion(
    db: Session, case: StudentCase, recorded_by: int | None = None
) -> CaseStageCompletion:
    """重算该总案当前版本的阶段完成度（打卡/批量每日记录后调用）。"""
    version = case.version or 1
    tasks = (
        db.query(CaseTask)
        .filter(CaseTask.student_case_id == case.id, CaseTask.version == version)
        .all()
    )
    # 兼容历史数据：老任务 version=1 且总案 version=1 时天然归属；若总案已升级但
    # 老任务无版本标记，则把未标记版本差异的任务也纳入当前版本统计。
    if not tasks:
        tasks = db.query(CaseTask).filter(CaseTask.student_case_id == case.id).all()
    latest = _latest_checkins_by_task(db, [t.id for t in tasks])
    total_points = sum(t.points or 0 for t in tasks)
    earned = 0.0
    completed = 0
    rates: list[int] = []
    per_task = []
    for task in tasks:
        checkin = latest.get(task.id)
        rate = checkin.completion_rate if checkin else 0
        rates.append(rate)
        if rate >= 100:
            completed += 1
        earned += checkin.earned_points if checkin else 0.0
        per_task.append({"task_id": task.id, "title": task.title, "rate": rate})
    avg_rate = round(sum(rates) / len(rates), 2) if rates else 0.0
    row = (
        db.query(CaseStageCompletion)
        .filter_by(student_case_id=case.id, version=version)
        .first()
    )
    if row is None:
        row = CaseStageCompletion(student_case_id=case.id, version=version)
        db.add(row)
    row.total_tasks = len(tasks)
    row.completed_tasks = completed
    row.avg_completion_rate = avg_rate
    row.total_points = total_points
    row.earned_points = round(earned, 2)
    row.detail = {"tasks": per_task}
    row.recorded_by = recorded_by
    db.flush()
    return row


def parse_week_label(label: str) -> tuple[date, date]:
    """解析 2026-W36 为当周周一~周日。"""
    try:
        year_s, week_s = label.split("-W")
        year, week = int(year_s), int(week_s)
        start = date.fromisocalendar(year, week, 1)
        return start, start + timedelta(days=6)
    except Exception as exc:
        raise ValueError("period_label 需为 YYYY-Www 格式，如 2026-W36") from exc


def parse_month_label(label: str) -> tuple[date, date]:
    try:
        y, m = map(int, label.split("-"))
        last = calendar.monthrange(y, m)[1]
        return date(y, m, 1), date(y, m, last)
    except Exception as exc:
        raise ValueError("period_label 需为 YYYY-MM 格式，如 2026-09") from exc


def current_week_label(today: date | None = None) -> str:
    today = today or date.today()
    iso_year, iso_week, _ = today.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def current_month_label(today: date | None = None) -> str:
    today = today or date.today()
    return f"{today.year}-{today.month:02d}"


def _checkin_log_date(row: TaskCheckin) -> date | None:
    if row.log_date is not None:
        return row.log_date
    if row.checked_in_at is not None:
        return row.checked_in_at.date()
    return None


def build_points_reports(
    db: Session,
    class_id: int,
    period_type: str,
    period_label: str,
    recorded_by: int | None = None,
) -> list[StudentPointsReport]:
    """按周期从每日打卡累加积分，一学生一周期一条（幂等 upsert）。"""
    if period_type == "weekly":
        start, end = parse_week_label(period_label)
    elif period_type == "monthly":
        start, end = parse_month_label(period_label)
    else:
        raise ValueError("period_type 仅支持 weekly/monthly")
    members = db.query(ClassStudent).filter_by(class_id=class_id).all()
    if not members:
        raise ValueError("该班级暂无学生")
    results: list[StudentPointsReport] = []
    for member in members:
        case = (
            db.query(StudentCase)
            .filter_by(class_id=class_id, student_id=member.student_id)
            .order_by(StudentCase.updated_at.desc())
            .first()
        )
        task_ids: list[int] = []
        task_points: dict[int, int] = {}
        if case is not None:
            for task in db.query(CaseTask).filter_by(student_case_id=case.id).all():
                task_ids.append(task.id)
                task_points[task.id] = task.points or 0
        earned = 0.0
        checkin_count = 0
        per_task_earned: dict[int, float] = {}
        if task_ids:
            rows = db.query(TaskCheckin).filter(TaskCheckin.task_id.in_(task_ids)).all()
            seen: dict[tuple[int, date], TaskCheckin] = {}
            for row in rows:
                log_date = _checkin_log_date(row)
                if log_date is None or not (start <= log_date <= end):
                    continue
                key = (row.task_id, log_date)
                prev = seen.get(key)
                if prev is None or (row.checked_in_at and prev.checked_in_at and row.checked_in_at > prev.checked_in_at):
                    seen[key] = row
            for (task_id, _), row in seen.items():
                earned += row.earned_points or 0.0
                checkin_count += 1
                per_task_earned[task_id] = round(per_task_earned.get(task_id, 0.0) + (row.earned_points or 0.0), 2)
        total = round(sum(task_points.values()), 2)
        earned = round(earned, 2)
        rate = round(earned / total * 100, 2) if total else 0.0
        report = (
            db.query(StudentPointsReport)
            .filter_by(student_id=member.student_id, period_type=period_type, period_label=period_label)
            .first()
        )
        if report is None:
            report = StudentPointsReport(
                student_id=member.student_id,
                class_id=class_id,
                student_case_id=case.id if case else None,
                period_type=period_type,
                period_label=period_label,
                period_start=start,
                period_end=end,
            )
            db.add(report)
        report.class_id = class_id
        report.student_case_id = case.id if case else None
        report.period_start = start
        report.period_end = end
        report.total_points = total
        report.earned_points = earned
        report.completion_rate = rate
        report.task_count = len(task_ids)
        report.checkin_count = checkin_count
        report.detail = {"per_task_earned": {str(k): v for k, v in per_task_earned.items()}}
        report.recorded_by = recorded_by
        results.append(report)
    db.flush()
    return results


def enrich_points_report(db: Session, report: StudentPointsReport) -> dict:
    stu = db.get(User, report.student_id)
    cls = db.get(Class, report.class_id)
    from app.schemas.case_points import PointsReportOut

    data = PointsReportOut.model_validate(report).model_dump()
    data["student_name"] = stu.name if stu else None
    data["class_name"] = cls.name if cls else None
    return data
