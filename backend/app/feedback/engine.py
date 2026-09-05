"""课后反馈生成引擎：构建输入快照并调用 LLM 生成反馈文本。

快照只包含脱敏的学情数据（student_alias 代替姓名），模型禁止编造数据。
"""

import json
from datetime import date, datetime, time, timezone

from sqlalchemy.orm import Session

from app.ai.provider import LLMResponse, get_llm_provider
from app.analytics.service import (
    get_student_knowledge_stats,
    get_student_repeated_errors,
    get_student_weak_points,
)
from app.models.assignment import Assignment
from app.models.feedback import FEEDBACK_TYPE_ASSIGNMENT, FEEDBACK_TYPE_WEEKLY
from app.models.submission import SUBMISSION_STATUS_TEACHER_REVIEWED, Submission, SubmissionAnswer

PROMPT_VERSION = "feedback_v1"
SYSTEM_PROMPT = """你是一名严谨的教师助手。你只能依据提供的结构化学习数据生成课后反馈。
不得编造分数、知识点、错误或学习经历，不得推断学生身份。输出纯文本，300字以内。"""


def _json_safe(payload: dict) -> dict:
    """确保快照可 JSON 序列化：datetime 等类型转字符串。"""
    return json.loads(json.dumps(payload, ensure_ascii=False, default=str))


def _score(db: Session, submission: Submission) -> tuple[float, float, float]:
    """统计某提交的总分/满分/得分百分比。"""
    answers = db.query(SubmissionAnswer).filter(
        SubmissionAnswer.submission_id == submission.id
    ).all()
    total = round(sum(answer.score or 0 for answer in answers), 1)
    maximum = round(sum(answer.max_score or 0 for answer in answers), 1)
    percent = round(total / maximum * 100, 1) if maximum else 0.0
    return total, maximum, percent


def build_assignment_snapshot(
    db: Session, student_id: int, class_id: int, assignment_id: int
) -> dict:
    """构建单次作业反馈快照：分数、薄弱点、重复错误。"""
    assignment = db.get(Assignment, assignment_id)
    if assignment is None or assignment.class_id != class_id:
        raise ValueError("作业不属于指定班级")
    submission = (
        db.query(Submission)
        .filter(
            Submission.assignment_id == assignment_id,
            Submission.student_id == student_id,
            Submission.status == SUBMISSION_STATUS_TEACHER_REVIEWED,
        )
        .order_by(Submission.submitted_at.desc())
        .first()
    )
    if submission is None:
        raise ValueError("该学生尚无已确认的作业结果")
    total, maximum, percent = _score(db, submission)
    return _json_safe({
        "student_alias": f"student_{student_id}",
        "report_type": FEEDBACK_TYPE_ASSIGNMENT,
        "class_id": class_id,
        "assignment": {
            "id": assignment.id,
            "title": assignment.title,
            "score": total,
            "max_score": maximum,
            "percent": percent,
        },
        "weak_points": get_student_weak_points(
            db, student_id, top_n=3, min_records=1, class_id=class_id
        ),
        "repeated_errors": get_student_repeated_errors(
            db, student_id, top_n=5, min_count=2, class_id=class_id
        ),
    })


def build_weekly_snapshot(
    db: Session,
    student_id: int,
    class_id: int,
    period_start: date,
    period_end: date,
) -> dict:
    """构建周反馈快照：周期内所有已确认作业得分与整体学情。"""
    # 时间范围：起始日 00:00 ~ 结束日 23:59:59
    start_at = datetime.combine(period_start, time.min, tzinfo=timezone.utc)
    end_at = datetime.combine(period_end, time.max, tzinfo=timezone.utc)
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
    scores = []
    for submission in submissions:
        total, maximum, percent = _score(db, submission)
        scores.append(
            {
                "assignment_id": submission.assignment_id,
                "score": total,
                "max_score": maximum,
                "percent": percent,
            }
        )
    return _json_safe({
        "student_alias": f"student_{student_id}",
        "report_type": FEEDBACK_TYPE_WEEKLY,
        "class_id": class_id,
        "period": {"start": period_start.isoformat(), "end": period_end.isoformat()},
        "assignment_count": len(scores),
        "average_percent": (
            round(sum(item["percent"] for item in scores) / len(scores), 1)
            if scores
            else 0.0
        ),
        "scores": scores,
        "knowledge_stats": get_student_knowledge_stats(db, student_id, class_id),
        "weak_points": get_student_weak_points(
            db, student_id, top_n=3, min_records=1, class_id=class_id
        ),
        "repeated_errors": get_student_repeated_errors(
            db, student_id, top_n=5, min_count=2, class_id=class_id
        ),
    })


def generate_feedback(snapshot: dict) -> LLMResponse:
    """调用 LLM 依据快照生成反馈文本，空结果报错、超长截断。"""
    user = """根据以下真实结构化学习数据生成反馈。
要求：先说明本次或本周表现；指出1至3个薄弱知识点；说明重复错误（没有则明确暂无）；给出可执行的下一步建议。
<feedback_data>
{data}
</feedback_data>""".format(data=json.dumps(snapshot, ensure_ascii=False, default=str))
    response = get_llm_provider().chat_with_metadata(SYSTEM_PROMPT, user)
    content = response.text.strip()
    if not content:
        raise ValueError("模型返回了空反馈")
    response.text = content[:600]
    return response
