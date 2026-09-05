"""月度评价生成引擎：汇总月度学情 + 德育表现，调用 LLM 生成结构化月度评价。"""

import calendar
import json
from datetime import date, datetime, time, timezone

from sqlalchemy.orm import Session

from app.ai.provider import LLMResponse, get_llm_provider
from app.analytics.service import get_student_knowledge_stats, get_student_weak_points
from app.models.assignment import Assignment
from app.models.student_case import CaseReview, CaseTask, StudentCase, SubjectPlan, TaskCheckin
from app.models.submission import SUBMISSION_STATUS_TEACHER_REVIEWED, Submission, SubmissionAnswer
from app.models.weekly_score import WeeklyTestScore

PROMPT_VERSION = "monthly_v1"
SYSTEM_PROMPT = """你是一名严谨的高三班主任助手。你只能依据提供的结构化月度数据生成学生月度评价。
禁止编造分数、排名、行为或不存在的事件。输出必须包含三个小节标题：
## 学情总结
## 德育表现
## 改进方案
每节 150-300 字，语言专业克制，面向家长可读。"""

def _json_safe(payload: dict) -> dict:
    return json.loads(json.dumps(payload, ensure_ascii=False, default=str))

def _month_bounds(month_label: str) -> tuple[date, date]:
    y, m = map(int, month_label.split("-"))
    last = calendar.monthrange(y, m)[1]
    return date(y, m, 1), date(y, m, last)

def _score(db: Session, submission: Submission) -> tuple[float, float, float]:
    answers = db.query(SubmissionAnswer).filter(SubmissionAnswer.submission_id == submission.id).all()
    total = round(sum(a.score or 0 for a in answers), 1)
    maximum = round(sum(a.max_score or 0 for a in answers), 1)
    percent = round(total / maximum * 100, 1) if maximum else 0.0
    return total, maximum, percent

def build_monthly_snapshot(
    db: Session,
    student_id: int,
    class_id: int,
    month_label: str,
    student_case_id: int | None = None,
) -> dict:
    period_start, period_end = _month_bounds(month_label)
    start_at = datetime.combine(period_start, time.min, tzinfo=timezone.utc)
    end_at = datetime.combine(period_end, time.max, tzinfo=timezone.utc)

    # 周测成绩
    weekly_rows = (
        db.query(WeeklyTestScore)
        .filter(
            WeeklyTestScore.student_id == student_id,
            WeeklyTestScore.class_id == class_id,
            WeeklyTestScore.exam_date >= period_start,
            WeeklyTestScore.exam_date <= period_end,
        )
        .order_by(WeeklyTestScore.exam_date.asc())
        .all()
    )
    weekly_scores = [
        {"subject": r.subject, "exam_date": r.exam_date.isoformat(), "exam_name": r.exam_name, "score": r.score, "max_score": r.max_score, "rank": r.rank_in_class}
        for r in weekly_rows
    ]
    # 作业得分
    submissions = (
        db.query(Submission)
        .join(Assignment, Assignment.id == Submission.assignment_id)
        .filter(
            Submission.student_id == student_id,
            Submission.status == SUBMISSION_STATUS_TEACHER_REVIEWED,
            Assignment.class_id == class_id,
            Submission.submitted_at >= start_at,
            Submission.submitted_at <= end_at,
        )
        .order_by(Submission.submitted_at.asc())
        .all()
    )
    assignment_scores = []
    for sub in submissions:
        total, maximum, percent = _score(db, sub)
        assignment_scores.append({"assignment_id": sub.assignment_id, "score": total, "max_score": maximum, "percent": percent, "submitted_at": sub.submitted_at.isoformat()})

    # 一生一案数据（若有关联）
    case = None
    if student_case_id:
        case = db.get(StudentCase, student_case_id)
    else:
        case = db.query(StudentCase).filter(StudentCase.student_id == student_id, StudentCase.class_id == class_id).order_by(StudentCase.updated_at.desc()).first()

    tasks, checkins, reviews, moral_plan = [], [], [], None
    if case:
        tasks = db.query(CaseTask).filter(CaseTask.student_case_id == case.id, CaseTask.starts_on <= period_end, CaseTask.due_on >= period_start).all()
        task_ids = [t.id for t in tasks]
        if task_ids:
            checkins = db.query(TaskCheckin).filter(TaskCheckin.task_id.in_(task_ids)).all()
            # 仅保留当月打卡
            checkins = [c for c in checkins if period_start <= c.checked_in_at.date() <= period_end] if checkins else []
        reviews = db.query(CaseReview).filter(CaseReview.student_case_id == case.id, CaseReview.reviewed_at >= start_at, CaseReview.reviewed_at <= end_at).all()
        moral_plan = db.query(SubjectPlan).filter(SubjectPlan.student_case_id == case.id, SubjectPlan.subject == "德育").first()

    avg_percent = round(sum(s["percent"] for s in assignment_scores) / len(assignment_scores), 1) if assignment_scores else 0

    snapshot = {
        "student_alias": f"student_{student_id}",
        "month_label": month_label,
        "period": {"start": period_start.isoformat(), "end": period_end.isoformat()},
        "class_id": class_id,
        "student_case_id": case.id if case else None,
        "weekly_scores": weekly_scores,
        "weekly_count": len(weekly_scores),
        "weekly_avg": round(sum(s["score"] for s in weekly_scores) / len(weekly_scores), 1) if weekly_scores else None,
        "assignments": {"count": len(assignment_scores), "average_percent": avg_percent, "scores": assignment_scores},
        "knowledge_stats": get_student_knowledge_stats(db, student_id, class_id),
        "weak_points": get_student_weak_points(db, student_id, top_n=3, min_records=1, class_id=class_id),
        "case": {
            "tasks": [{"subject": t.subject, "title": t.title, "status": t.status, "due_on": t.due_on.isoformat()} for t in tasks],
            "checkins": [{"task_id": c.task_id, "completion_rate": c.completion_rate, "self_check": c.self_check[:120]} for c in checkins],
            "reviews": [{"level": r.review_level, "subject": r.subject, "problem": r.problem[:120], "corrective_action": r.corrective_action[:120]} for r in reviews],
            "moral_plan": {
                "problem_location": (moral_plan.problem_location[:200] if moral_plan and moral_plan.problem_location else ""),
                "cause_analysis": (moral_plan.cause_analysis[:200] if moral_plan and moral_plan.cause_analysis else ""),
                "reinforcement": (moral_plan.reinforcement[:200] if moral_plan and moral_plan.reinforcement else ""),
            } if moral_plan else None,
            "overall_problem": (case.overall_problem[:300] if case and case.overall_problem else ""),
            "current_summary": (case.current_summary[:300] if case and case.current_summary else ""),
        },
    }
    return _json_safe(snapshot)

def generate_monthly_report(snapshot: dict) -> LLMResponse:
    user = """根据以下真实月度结构化数据生成学生月度评价，严格分为三节，不得编造。
<monthly_data>
{data}
</monthly_data>
要求：
- 学情总结：概括周测与作业表现、均分趋势、薄弱知识点
- 德育表现：总结行为表现、原因与日常优化措施
- 改进方案：给出下月可执行的 3-4 条具体措施，含目标与检查节点
""".format(data=json.dumps(snapshot, ensure_ascii=False))
    response = get_llm_provider().chat_with_metadata(SYSTEM_PROMPT, user)
    content = response.text.strip()
    if not content:
        raise ValueError("模型返回了空月度评价")
    response.text = content[:4000]
    return response
