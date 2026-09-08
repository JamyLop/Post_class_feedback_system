"""阶段完成度重算与积分周报/月报累加逻辑。

积分口径（新）：
- 每个学生的每个任务每天满分 1 分，按打卡完成度折算：earned = completion_rate / 100。
- 同一学生同一科目同一天多任务合计封顶 1 分。
- 同一学生一门科目自然周（周一~周日）封顶 7 分。
- 周任务创建时必须明确每周执行次数（weekly_times 1-7），用于计算周期应得满分。
"""

import calendar
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.case_points import CaseStageCompletion, StudentPointsReport
from app.models.class_ import Class, ClassStudent
from app.models.student_case import CaseTask, StudentCase, TaskCheckin
from app.models.user import User

DAILY_TASK_POINT = 1.0
DAILY_SUBJECT_CAP = 1.0
WEEKLY_SUBJECT_CAP = 7.0


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


def earned_of(task_points: int | float | None = None, rate: int | float | None = None, **kwargs) -> float:
    """每天每任务满分 1 分，按完成度折算（兼容旧 earned_of(points, rate) 签名）。

    支持两种调用：earned_of(points, rate) / earned_of(rate) / earned_of(rate=xx)。
    task_points 仅为兼容历史调用保留，不再参与计算。
    """
    if rate is None:
        # 兼容 earned_of(rate) 单参调用
        rate = task_points if task_points is not None else 0
    try:
        r = float(rate or 0)
    except (TypeError, ValueError):
        r = 0.0
    r = max(0.0, min(100.0, r))
    return round(min(DAILY_TASK_POINT, r / 100.0 * DAILY_TASK_POINT), 2)


def _subject_of(task: CaseTask) -> str:
    return (task.subject or "").strip() or "未分科"


def recompute_stage_completion(
    db: Session, case: StudentCase, recorded_by: int | None = None
) -> CaseStageCompletion:
    """重算该总案当前版本的阶段完成度（打卡/批量每日记录后调用）。

    阶段口径：每个任务满分 1 分，取各任务最新一条打卡的完成度折算。
    """
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
        earned += earned_of(rate) if checkin else 0.0
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
    # 阶段满分：每任务 1 分
    row.total_points = len(tasks)
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


def _iter_weeks(start: date, end: date) -> list[tuple[date, date]]:
    """把 [start, end] 按自然周切分，每段为该周落在本周期内的交集。"""
    weeks: list[tuple[date, date]] = []
    cur = start - timedelta(days=start.weekday())  # 本周期首日所在周一
    while cur <= end:
        w_start = max(cur, start)
        w_end = min(cur + timedelta(days=6), end)
        if w_start <= w_end:
            weeks.append((w_start, w_end))
        cur += timedelta(days=7)
    return weeks


def _expected_total(
    tasks: list[CaseTask], start: date, end: date, period_type: str
) -> tuple[float, dict[str, float]]:
    """计算周期应得满分：按周任务执行次数 + 日任务天数，加总后单科封顶。

    - 日任务：该周内与任务有效期重叠的天数 × 1 分；
    - 周任务：每周 weekly_times 分（任务当周有效才计）；
    - 月任务：整个周期计 1 分；
    - 单科每周封顶 7 分；周报总满分 = 各科周封顶之和；
      月报总满分 = 各自然周分段封顶求和（月任务另 +1/科，仍受当月天数上限约束）。
    """
    if not tasks:
        return 0.0, {}
    by_subject: dict[str, list[CaseTask]] = {}
    for t in tasks:
        by_subject.setdefault(_subject_of(t), []).append(t)
    per_subject_total: dict[str, float] = {}
    days_in_period = (end - start).days + 1
    if period_type == "weekly":
        for subject, sub_tasks in by_subject.items():
            exp = 0.0
            for t in sub_tasks:
                if t.due_on < start or t.starts_on > end:
                    continue
                if (t.cadence or "") == "weekly":
                    exp += float(t.weekly_times or 0)
                elif (t.cadence or "") == "monthly":
                    exp += 1.0
                else:  # daily 及其他按日计
                    overlap_start = max(t.starts_on, start)
                    overlap_end = min(t.due_on, end)
                    days = (overlap_end - overlap_start).days + 1
                    exp += max(0, days) * DAILY_TASK_POINT
            per_subject_total[subject] = round(min(WEEKLY_SUBJECT_CAP, exp), 2)
        total = round(sum(per_subject_total.values()), 2)
        return total, per_subject_total
    # monthly：按自然周分段求期望再求和，避免跨月周被高估
    for subject, sub_tasks in by_subject.items():
        sub_total = 0.0
        for w_start, w_end in _iter_weeks(start, end):
            exp_week = 0.0
            for t in sub_tasks:
                if t.due_on < w_start or t.starts_on > w_end:
                    continue
                if (t.cadence or "") == "weekly":
                    exp_week += float(t.weekly_times or 0)
                elif (t.cadence or "") == "monthly":
                    continue  # 月任务不在周分段内重复计，周期末统一 +1
                else:
                    overlap_start = max(t.starts_on, w_start)
                    overlap_end = min(t.due_on, w_end)
                    days = (overlap_end - overlap_start).days + 1
                    exp_week += max(0, days) * DAILY_TASK_POINT
            sub_total += min(WEEKLY_SUBJECT_CAP, exp_week)
        monthly_extra = sum(
            1.0 for t in sub_tasks
            if (t.cadence or "") == "monthly" and not (t.due_on < start or t.starts_on > end)
        )
        sub_total += monthly_extra
        # 月度单科满分不超过当月天数（每天 1 分上限）
        per_subject_total[subject] = round(min(float(days_in_period), sub_total), 2)
    total = round(sum(per_subject_total.values()), 2)
    return total, per_subject_total


def _capped_earned(
    deduped: list[tuple[CaseTask, TaskCheckin, date]],
) -> tuple[float, dict[str, float], dict[int, float]]:
    """按“单科单日封顶 1 分、单科自然周封顶 7 分”汇总实得积分。"""
    # 先按 (subject, log_date) 聚合再封顶到 1 分/天
    daily: dict[tuple[str, date], float] = {}
    per_task_earned: dict[int, float] = {}
    for task, row, log_date in deduped:
        e = earned_of(row.completion_rate)
        per_task_earned[task.id] = round(per_task_earned.get(task.id, 0.0) + e, 2)
        key = (_subject_of(task), log_date)
        daily[key] = daily.get(key, 0.0) + e
    for key in list(daily):
        daily[key] = round(min(DAILY_SUBJECT_CAP, daily[key]), 2)
    # 再按 (subject, ISO周) 聚合封顶到 7 分/周
    weekly: dict[tuple[str, tuple[int, int]], float] = {}
    for (subject, log_date), val in daily.items():
        iso_year, iso_week, _ = log_date.isocalendar()
        wkey = (subject, (iso_year, iso_week))
        weekly[wkey] = weekly.get(wkey, 0.0) + val
    per_subject_earned: dict[str, float] = {}
    for (subject, _), val in weekly.items():
        per_subject_earned[subject] = per_subject_earned.get(subject, 0.0) + min(
            WEEKLY_SUBJECT_CAP, val
        )
    for subject in list(per_subject_earned):
        per_subject_earned[subject] = round(per_subject_earned[subject], 2)
    total_earned = round(sum(per_subject_earned.values()), 2)
    return total_earned, per_subject_earned, per_task_earned


def build_points_reports(
    db: Session,
    class_id: int,
    period_type: str,
    period_label: str,
    recorded_by: int | None = None,
) -> list[StudentPointsReport]:
    """按周期从每日打卡累加积分，一学生一周期一条（幂等 upsert）。

    新口径：每天每任务满分 1 分按完成度折算，单科单日封顶 1 分、单科自然周封顶 7 分。
    同一任务同一天多次打卡仅取最新一条，不重复计分。
    """
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
        tasks: list[CaseTask] = []
        task_map: dict[int, CaseTask] = {}
        if case is not None:
            tasks = db.query(CaseTask).filter_by(student_case_id=case.id).all()
            task_map = {t.id: t for t in tasks}
        earned = 0.0
        checkin_count = 0
        per_task_earned: dict[int, float] = {}
        per_subject_earned: dict[str, float] = {}
        if task_map:
            rows = db.query(TaskCheckin).filter(TaskCheckin.task_id.in_(list(task_map))).all()
            seen: dict[tuple[int, date], TaskCheckin] = {}
            for row in rows:
                log_date = _checkin_log_date(row)
                if log_date is None or not (start <= log_date <= end):
                    continue
                key = (row.task_id, log_date)
                prev = seen.get(key)
                if prev is None or (row.checked_in_at and prev.checked_in_at and row.checked_in_at > prev.checked_in_at):
                    seen[key] = row
            deduped: list[tuple[CaseTask, TaskCheckin, date]] = []
            for (task_id, log_date), row in seen.items():
                task = task_map.get(task_id)
                if task is None:
                    continue
                deduped.append((task, row, log_date))
            checkin_count = len(deduped)
            earned, per_subject_earned, per_task_earned = _capped_earned(deduped)
        total, per_subject_total = _expected_total(tasks, start, end, period_type)
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
        report.task_count = len(tasks)
        report.checkin_count = checkin_count
        report.detail = {
            "per_task_earned": {str(k): v for k, v in per_task_earned.items()},
            "per_subject_earned": per_subject_earned,
            "per_subject_total": per_subject_total,
            "rule": "daily-1-point_subject-weekly-cap-7",
        }
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
