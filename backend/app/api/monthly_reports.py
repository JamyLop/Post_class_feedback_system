"""月度评定 API：教师手动填写、保存与发布。"""

import calendar
import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.class_ import Class, ClassStudent, StudentGuardian
from app.models.monthly_report import (
    MONTHLY_STATUS_FAILED,
    MONTHLY_STATUS_GENERATED,
    MONTHLY_STATUS_GENERATING,
    MONTHLY_STATUS_PUBLISHED,
    MonthlyReport,
)
from app.models.student_case import StudentCase
from app.models.user import ROLE_ADMIN, ROLE_PARENT, ROLE_STUDENT, ROLE_TEACHER, User
from app.schemas.monthly_report import MonthlyReportCreateIn, MonthlyReportOut, MonthlyReportUpdateIn

router = APIRouter(prefix="/monthly-reports", tags=["monthly-reports"])
_manager = require_roles([ROLE_ADMIN, ROLE_TEACHER])
logger = logging.getLogger(__name__)

def _month_bounds(label: str) -> tuple[date, date]:
    try:
        y, m = map(int, label.split("-"))
        last = calendar.monthrange(y, m)[1]
        return date(y, m, 1), date(y, m, last)
    except Exception:
        raise HTTPException(status_code=400, detail="month_label 需为 YYYY-MM 格式")

def _enrich(row: MonthlyReport, db: Session) -> dict:
    data = MonthlyReportOut.model_validate(row).model_dump()
    stu = db.get(User, row.student_id)
    cls = db.get(Class, row.class_id)
    data["student_name"] = stu.name if stu else None
    data["class_name"] = cls.name if cls else None
    return data

def _authorize_student_class(db: Session, student_id: int, class_id: int, user: User):
    cls = db.get(Class, class_id)
    if cls is None:
        raise HTTPException(status_code=404, detail="班级不存在")
    if user.role == ROLE_TEACHER and cls.teacher_id != user.id:
        # 也允许通过 ClassTeacher 关联
        from app.models.class_ import ClassTeacher
        if not db.query(ClassTeacher).filter_by(class_id=class_id, teacher_id=user.id).first():
            raise HTTPException(status_code=403, detail="无权操作该班级月度评定")
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
    _authorize_student_class(db, body.student_id, body.class_id, user)
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
        raise HTTPException(status_code=409, detail="该学生本月已有评定，请打开原评定编辑")
    report = MonthlyReport(
        student_id=body.student_id, class_id=body.class_id,
        student_case_id=body.student_case_id, month_label=body.month_label,
        period_start=period_start, period_end=period_end,
        # 沿用 generated 存储值表示待发布，兼容历史记录且无需迁移。
        status=MONTHLY_STATUS_GENERATED, final_content=body.final_content,
        reviewed_by=user.id, prompt_version="manual_v1", input_snapshot={},
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return _enrich(report, db)

@router.get("", response_model=list[MonthlyReportOut])
def list_reports(
    student_id: int | None = Query(default=None),
    class_id: int | None = Query(default=None),
    month_label: str | None = Query(default=None),
    status: str | None = Query(default=None),
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
        from app.models.class_ import ClassTeacher
        legacy_ids = [r.id for r in db.query(Class).filter(Class.teacher_id == user.id).all()]
        rel_ids = [r.class_id for r in db.query(ClassTeacher).filter(ClassTeacher.teacher_id == user.id).all()]
        allowed = set(legacy_ids + rel_ids)
        if not allowed:
            return []
        q = q.filter(MonthlyReport.class_id.in_(allowed))
    # 管理员不过滤
    if student_id is not None:
        q = q.filter(MonthlyReport.student_id == student_id)
    if class_id is not None:
        q = q.filter(MonthlyReport.class_id == class_id)
    if month_label:
        q = q.filter(MonthlyReport.month_label == month_label)
    if status:
        q = q.filter(MonthlyReport.status == status)
    rows = q.order_by(MonthlyReport.month_label.desc(), MonthlyReport.created_at.desc()).all()
    return [_enrich(r, db) for r in rows]

@router.get("/{report_id}", response_model=MonthlyReportOut)
def get_report(report_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = _report_access(db, report_id, user)
    return _enrich(r, db)

@router.put("/{report_id}", response_model=MonthlyReportOut)
def update_report(report_id: int, body: MonthlyReportUpdateIn, db: Session = Depends(get_db), user: User = Depends(_manager)):
    r = _report_access(db, report_id, user)
    # 旧的失败/排队记录可由教师接手，保存后进入待发布状态。
    if r.status in (MONTHLY_STATUS_GENERATING, MONTHLY_STATUS_FAILED):
        r.status = MONTHLY_STATUS_GENERATED
        r.error_message = ""
    r.final_content = body.final_content.strip()
    r.reviewed_by = user.id
    if r.status == MONTHLY_STATUS_PUBLISHED:
        from datetime import datetime, timezone
        r.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(r)
    logger.info("monthly_updated report_id=%s teacher_id=%s", r.id, user.id)
    return _enrich(r, db)

@router.post("/{report_id}/publish", response_model=MonthlyReportOut)
def publish_report(report_id: int, db: Session = Depends(get_db), user: User = Depends(_manager)):
    r = _report_access(db, report_id, user)
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
    return _enrich(r, db)

@router.delete("/{report_id}")
def delete_report(report_id: int, db: Session = Depends(get_db), user: User = Depends(_manager)):
    r = _report_access(db, report_id, user)
    db.delete(r)
    db.commit()
    return {"ok": True}
