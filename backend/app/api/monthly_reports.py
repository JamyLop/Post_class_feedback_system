"""月度评定 API：班主任手动填写、保存与发布；任课老师独立提交学科评价。"""

import calendar
import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.class_ import Class, ClassStudent, ClassTeacher, StudentGuardian
from app.models.monthly_report import (
    MONTHLY_EVAL_ROLE_HEAD,
    MONTHLY_EVAL_ROLE_SUBJECT,
    MONTHLY_STATUS_FAILED,
    MONTHLY_STATUS_GENERATED,
    MONTHLY_STATUS_GENERATING,
    MONTHLY_STATUS_PUBLISHED,
    MonthlyReport,
    MonthlyReportEvaluation,
)
from app.models.student_case import StudentCase, SubjectPlan
from app.models.user import (
    ROLE_ADMIN,
    ROLE_PARENT,
    ROLE_STUDENT,
    ROLE_SUBJECT_TEACHER,
    ROLE_TEACHER,
    User,
)
from app.schemas.monthly_report import (
    MonthlyEvaluationSave,
    MonthlyReportCreateIn,
    MonthlyReportOut,
    MonthlyReportUpdateIn,
)

router = APIRouter(prefix="/monthly-reports", tags=["monthly-reports"])
_manager = require_roles([ROLE_ADMIN, ROLE_TEACHER, ROLE_SUBJECT_TEACHER])
_evaluator = require_roles([ROLE_TEACHER, ROLE_SUBJECT_TEACHER])
logger = logging.getLogger(__name__)

def _month_bounds(label: str) -> tuple[date, date]:
    try:
        y, m = map(int, label.split("-"))
        last = calendar.monthrange(y, m)[1]
        return date(y, m, 1), date(y, m, last)
    except Exception:
        raise HTTPException(status_code=400, detail="month_label 需为 YYYY-MM 格式")

def _enrich(row: MonthlyReport, db: Session, user: User) -> dict:
    data = MonthlyReportOut.model_validate(row).model_dump()
    stu = db.get(User, row.student_id)
    cls = db.get(Class, row.class_id)
    data["student_name"] = stu.name if stu else None
    data["class_name"] = cls.name if cls else None
    role_subject = _evaluation_role(db, row, user)
    data["can_evaluate"] = role_subject is not None
    data["evaluation_subject"] = role_subject[1] if role_subject else ""
    data["can_manage"] = _is_head_teacher(db, row.class_id, user)
    data["can_publish"] = data["can_manage"] or user.role == ROLE_ADMIN
    return data


def _evaluation_role(db: Session, row: MonthlyReport, user: User) -> tuple[str, str] | None:
    """判定用户可否评价该月度评定；返回 (role, subject)，班主任 subject 为空。"""
    if user.role not in (ROLE_TEACHER, ROLE_SUBJECT_TEACHER):
        return None
    cls = db.get(Class, row.class_id)
    relations = db.query(ClassTeacher).filter_by(class_id=row.class_id, teacher_id=user.id).all()
    is_head = (cls is not None and cls.teacher_id == user.id) or any(r.role == "head_teacher" for r in relations)
    # 学生档案中的任课安排优先于班级关系，避免同班其他老师代填。
    case = db.get(StudentCase, row.student_case_id) if row.student_case_id else db.query(StudentCase).filter_by(
        student_id=row.student_id, class_id=row.class_id,
    ).filter(StudentCase.status != "archived").order_by(StudentCase.id.desc()).first()
    plans = db.query(SubjectPlan).filter_by(student_case_id=case.id).all() if case else []
    assigned = {p.subject for p in plans if p.teacher_id == user.id}
    configured = {p.subject for p in plans}
    assigned.update(r.subject for r in relations if r.role == "subject_teacher" and r.subject and r.subject not in configured)
    if assigned:
        return (MONTHLY_EVAL_ROLE_SUBJECT, "、".join(sorted(assigned)))
    if is_head:
        return (MONTHLY_EVAL_ROLE_HEAD, "")
    return None


def _is_head_teacher(db: Session, class_id: int, user: User) -> bool:
    if user.role not in (ROLE_TEACHER, ROLE_SUBJECT_TEACHER):
        return False
    cls = db.get(Class, class_id)
    return bool((cls and cls.teacher_id == user.id) or db.query(ClassTeacher).filter_by(
        class_id=class_id, teacher_id=user.id, role="head_teacher",
    ).first())


def _require_manager(db: Session, class_id: int, user: User):
    # 管理员保留发布管理权限；德育正文只能由本班班主任填写。
    if not _is_head_teacher(db, class_id, user):
        raise HTTPException(status_code=403, detail="德育月度评定仅由本班班主任填写")


def _subject_teacher_class_ids(db: Session, user: User) -> set[int]:
    rows = db.query(ClassTeacher).filter_by(teacher_id=user.id).all()
    plan_classes = db.query(StudentCase.class_id).join(SubjectPlan, SubjectPlan.student_case_id == StudentCase.id).filter(
        SubjectPlan.teacher_id == user.id, StudentCase.class_id.isnot(None), StudentCase.status != "archived",
    ).all()
    return {r.class_id for r in rows} | {r.class_id for r in plan_classes}

def _authorize_student_class(db: Session, student_id: int, class_id: int, user: User):
    cls = db.get(Class, class_id)
    if cls is None:
        raise HTTPException(status_code=404, detail="班级不存在")
    if user.role == ROLE_TEACHER and cls.teacher_id != user.id:
        # 也允许通过 ClassTeacher 关联
        if not db.query(ClassTeacher).filter_by(class_id=class_id, teacher_id=user.id).first():
            raise HTTPException(status_code=403, detail="无权操作该班级月度评定")
    if user.role == ROLE_SUBJECT_TEACHER:
        if not db.query(ClassTeacher).filter_by(class_id=class_id, teacher_id=user.id).first():
            raise HTTPException(status_code=403, detail="无权查看该班级月度评定")
    member = db.query(ClassStudent).filter(ClassStudent.class_id == class_id, ClassStudent.student_id == student_id).first()
    if member is None:
        raise HTTPException(status_code=403, detail="学生不属于该班级")

def _report_access(db: Session, report_id: int, user: User) -> MonthlyReport:
    r = db.get(MonthlyReport, report_id)
    if r is None:
        raise HTTPException(status_code=404, detail="月度评定不存在")
    if user.role == ROLE_ADMIN:
        return r
    if user.role == ROLE_STUDENT:
        if r.student_id != user.id or r.status != MONTHLY_STATUS_PUBLISHED:
            raise HTTPException(status_code=403, detail="无权查看该月度评定")
        return r
    if user.role == ROLE_PARENT:
        linked = db.query(StudentGuardian).filter_by(parent_id=user.id, student_id=r.student_id).first()
        if linked is None or r.status != MONTHLY_STATUS_PUBLISHED:
            raise HTTPException(status_code=403, detail="无权查看该月度评定")
        return r
    if _evaluation_role(db, r, user) is not None:
        return r
    if user.role == ROLE_SUBJECT_TEACHER:
        # 任课老师可查看所带班级的全部状态评定，以便在发布前提交学科评价。
        if not db.query(ClassTeacher).filter_by(class_id=r.class_id, teacher_id=user.id).first():
            raise HTTPException(status_code=403, detail="无权查看该月度评定")
        return r
    _authorize_student_class(db, r.student_id, r.class_id, user)
    return r

@router.post("/generate")
def generate_monthly(user: User = Depends(_manager)):
    # 老客户端必须升级，不能继续触发 AI 或覆盖教师已保存的正文。
    raise HTTPException(status_code=410, detail="月度评定已改为手动填写，请更新客户端后新建评定")


@router.post("", response_model=MonthlyReportOut)
def create_monthly(
    body: MonthlyReportCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(_manager),
):
    stu = db.get(User, body.student_id)
    if stu is None or stu.role != ROLE_STUDENT:
        raise HTTPException(status_code=404, detail="学生不存在")
    if not db.query(ClassStudent).filter_by(student_id=body.student_id, class_id=body.class_id).first():
        raise HTTPException(status_code=403, detail="学生不属于该班级")
    scope = MonthlyReport(student_id=body.student_id, class_id=body.class_id, student_case_id=body.student_case_id)
    role_subject = (MONTHLY_EVAL_ROLE_HEAD, "") if _is_head_teacher(db, body.class_id, user) else _evaluation_role(db, scope, user)
    if role_subject is None:
        raise HTTPException(status_code=403, detail="仅对应任课老师或本班班主任可填写")
    period_start, period_end = _month_bounds(body.month_label)
    if body.student_case_id is not None:
        sc = db.get(StudentCase, body.student_case_id)
        if sc is None or sc.student_id != body.student_id or sc.class_id != body.class_id:
            raise HTTPException(status_code=400, detail="student_case_id 与学生/班级不匹配")
    # 锁定学生，串行检查同班同月重复创建，防止双击或并发请求覆盖手写内容。
    db.query(User).filter(User.id == body.student_id).with_for_update().first()
    existing = db.query(MonthlyReport).filter_by(
        student_id=body.student_id, class_id=body.class_id, month_label=body.month_label,
    ).first()
    if existing:
        # 任课老师先填写后，班主任可补上德育，不覆盖已提交的学科内容。
        if role_subject[0] == MONTHLY_EVAL_ROLE_HEAD and not existing.final_content.strip():
            existing.final_content = body.final_content
            existing.reviewed_by = user.id
            db.commit()
            db.refresh(existing)
            return _enrich(existing, db, user)
        raise HTTPException(status_code=409, detail="该学生本月已有评定，请打开原评定填写")
    report = MonthlyReport(
        student_id=body.student_id, class_id=body.class_id,
        student_case_id=body.student_case_id, month_label=body.month_label,
        period_start=period_start, period_end=period_end,
        # 沿用 generated 存储值表示待发布，兼容历史记录且无需迁移。
        status=MONTHLY_STATUS_GENERATED, final_content=body.final_content if role_subject[0] == MONTHLY_EVAL_ROLE_HEAD else "",
        reviewed_by=user.id, prompt_version="manual_v1", input_snapshot={},
    )
    db.add(report)
    if role_subject[0] == MONTHLY_EVAL_ROLE_SUBJECT:
        # 学科老师可直接开始本月评定，无需等待班主任先建记录。
        if len(body.final_content) > 2000:
            raise HTTPException(status_code=422, detail="学科评定最多2000字")
        report.evaluations.append(MonthlyReportEvaluation(
            teacher_id=user.id, teacher_name=user.name, teacher_role=role_subject[0],
            subject=role_subject[1], content=body.final_content,
        ))
    db.commit()
    db.refresh(report)
    return _enrich(report, db, user)

@router.get("", response_model=list[MonthlyReportOut])
def list_reports(
    student_id: int | None = Query(default=None),
    class_id: int | None = Query(default=None),
    month_label: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(MonthlyReport)
    if user.role == ROLE_STUDENT:
        q = q.filter(MonthlyReport.student_id == user.id, MonthlyReport.status == MONTHLY_STATUS_PUBLISHED)
    elif user.role == ROLE_PARENT:
        student_ids = [r.student_id for r in db.query(StudentGuardian).filter_by(parent_id=user.id).all()]
        if not student_ids:
            return []
        q = q.filter(MonthlyReport.student_id.in_(student_ids), MonthlyReport.status == MONTHLY_STATUS_PUBLISHED)
    elif user.role == ROLE_TEACHER:
        # 教师仅看自己班级
        legacy_ids = [r.id for r in db.query(Class).filter(Class.teacher_id == user.id).all()]
        rel_ids = [r.class_id for r in db.query(ClassTeacher).filter(ClassTeacher.teacher_id == user.id).all()]
        allowed = set(legacy_ids + rel_ids) | _subject_teacher_class_ids(db, user)
        if not allowed:
            return []
        q = q.filter(MonthlyReport.class_id.in_(allowed))
    elif user.role == ROLE_SUBJECT_TEACHER:
        # 任课老师仅看所带班级（全部状态，以便发布前提交学科评价）。
        allowed = _subject_teacher_class_ids(db, user)
        if not allowed:
            return []
        q = q.filter(MonthlyReport.class_id.in_(allowed))
    elif user.role not in (ROLE_ADMIN,):
        # 德育主任、咨询老师等暂不开放月度评定列表。
        return []
    # 管理员不过滤
    if student_id is not None:
        q = q.filter(MonthlyReport.student_id == student_id)
    if class_id is not None:
        q = q.filter(MonthlyReport.class_id == class_id)
    if month_label:
        q = q.filter(MonthlyReport.month_label == month_label)
    if status:
        q = q.filter(MonthlyReport.status == status)
    rows = q.order_by(MonthlyReport.month_label.desc(), MonthlyReport.created_at.desc()).offset(offset).limit(limit).all()
    return [_enrich(r, db, user) for r in rows]

@router.get("/{report_id}", response_model=MonthlyReportOut)
def get_report(report_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = _report_access(db, report_id, user)
    return _enrich(r, db, user)

@router.put("/{report_id}", response_model=MonthlyReportOut)
def update_report(report_id: int, body: MonthlyReportUpdateIn, db: Session = Depends(get_db), user: User = Depends(_manager)):
    r = _report_access(db, report_id, user)
    _require_manager(db, r.class_id, user)
    # 旧的失败/排队记录可由教师接手，保存后进入待发布状态。
    if r.status in (MONTHLY_STATUS_GENERATING, MONTHLY_STATUS_FAILED):
        r.status = MONTHLY_STATUS_GENERATED
        r.error_message = ""
    r.final_content = body.final_content.strip()
    r.reviewed_by = user.id
    for evaluation in r.evaluations:
        if evaluation.teacher_role == MONTHLY_EVAL_ROLE_HEAD and evaluation.teacher_id == user.id:
            evaluation.content = r.final_content
    if r.status == MONTHLY_STATUS_PUBLISHED:
        from datetime import datetime, timezone
        r.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(r)
    logger.info("monthly_updated report_id=%s teacher_id=%s", r.id, user.id)
    return _enrich(r, db, user)

@router.post("/{report_id}/publish", response_model=MonthlyReportOut)
def publish_report(report_id: int, db: Session = Depends(get_db), user: User = Depends(_manager)):
    r = _report_access(db, report_id, user)
    if user.role != ROLE_ADMIN:
        _require_manager(db, r.class_id, user)
    if r.status != MONTHLY_STATUS_GENERATED:
        raise HTTPException(status_code=409, detail="只有待发布的月度评定可以发布")
    if not r.final_content.strip():
        raise HTTPException(status_code=409, detail="月度评定内容为空，不能发布")
    from datetime import datetime, timezone
    r.status = MONTHLY_STATUS_PUBLISHED
    r.reviewed_by = user.id
    r.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(r)
    logger.info("monthly_published report_id=%s teacher_id=%s", r.id, user.id)
    return _enrich(r, db, user)


@router.put("/{report_id}/evaluation", response_model=MonthlyReportOut)
def save_evaluation(
    report_id: int,
    body: MonthlyEvaluationSave,
    db: Session = Depends(get_db),
    user: User = Depends(_evaluator),
):
    # 同一份评定串行保存，避免重复点击或并发请求创建同一教师的重复评价。
    row = db.query(MonthlyReport).filter_by(id=report_id).with_for_update().first()
    if row is None:
        raise HTTPException(status_code=404, detail="月度评定不存在")
    # 先校验可见性（任课老师仅所带班级），再校验评价身份。
    _report_access(db, report_id, user)
    role_subject = _evaluation_role(db, row, user)
    if role_subject is None:
        raise HTTPException(status_code=403, detail="仅本班班主任和所带学科老师可评价")
    role, subject = role_subject
    evaluation = db.query(MonthlyReportEvaluation).filter_by(report_id=row.id, teacher_id=user.id).first()
    if evaluation is None:
        evaluation = MonthlyReportEvaluation(report_id=row.id, teacher_id=user.id)
        db.add(evaluation)
    evaluation.teacher_name = user.name
    evaluation.teacher_role = role
    evaluation.subject = subject
    evaluation.content = body.content
    if role == MONTHLY_EVAL_ROLE_HEAD:
        # 班主任的德育评价与主报告正文保持同一来源。
        row.final_content = body.content
        row.reviewed_by = user.id
    db.commit()
    db.refresh(row)
    logger.info("monthly_evaluated report_id=%s teacher_id=%s role=%s", row.id, user.id, role)
    return _enrich(row, db, user)

@router.delete("/{report_id}")
def delete_report(report_id: int, db: Session = Depends(get_db), user: User = Depends(_manager)):
    r = _report_access(db, report_id, user)
    if user.role != ROLE_ADMIN:
        _require_manager(db, r.class_id, user)
    db.delete(r)
    db.commit()
    return {"ok": True}
