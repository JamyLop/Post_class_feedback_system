"""一生一案业务规则：权限、状态机、版本快照与审计。"""

from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.models.class_ import Class, ClassStudent, ClassTeacher, StudentGuardian
from app.models.student_case import (
    CASE_STATUS_ADJUSTED,
    CASE_STATUS_ARCHIVED,
    CASE_STATUS_DRAFT,
    CASE_STATUS_EXECUTING,
    CASE_STATUS_PENDING_CONFIRMATION,
    CASE_STATUS_PENDING_REVIEW,
    CASE_STATUS_REVISION_REQUIRED,
    CaseAuditLog,
    CaseGoal,
    CaseReview,
    CaseStudentProfile,
    CaseTask,
    CaseVersion,
    StudentCase,
    SubjectPlan,
)
from app.models.user import ROLE_ADMIN, ROLE_DEYU_DIRECTOR, ROLE_PARENT, ROLE_STUDENT, ROLE_TEACHER, User

ALLOWED_TRANSITIONS = {
    CASE_STATUS_DRAFT: {CASE_STATUS_PENDING_CONFIRMATION},
    CASE_STATUS_PENDING_CONFIRMATION: {
        CASE_STATUS_DRAFT,
        CASE_STATUS_REVISION_REQUIRED,
        CASE_STATUS_EXECUTING,
    },
    CASE_STATUS_REVISION_REQUIRED: {CASE_STATUS_PENDING_CONFIRMATION},
    CASE_STATUS_EXECUTING: {CASE_STATUS_PENDING_REVIEW},
    CASE_STATUS_PENDING_REVIEW: {CASE_STATUS_ADJUSTED, CASE_STATUS_ARCHIVED},
    CASE_STATUS_ADJUSTED: {CASE_STATUS_EXECUTING, CASE_STATUS_PENDING_REVIEW},
    CASE_STATUS_ARCHIVED: set(),
}

PARENT_VISIBLE_STATUSES = {
    CASE_STATUS_EXECUTING,
    CASE_STATUS_PENDING_REVIEW,
    CASE_STATUS_ADJUSTED,
    CASE_STATUS_ARCHIVED,
}

# 学生自查可见状态与家长一致（仅已发布），独立常量以便后续差异化
STUDENT_VISIBLE_STATUSES = {
    CASE_STATUS_EXECUTING,
    CASE_STATUS_PENDING_REVIEW,
    CASE_STATUS_ADJUSTED,
    CASE_STATUS_ARCHIVED,
}


def class_teacher_scope(db: Session, class_id: int, teacher_id: int) -> list[ClassTeacher]:
    return db.query(ClassTeacher).filter(
        ClassTeacher.class_id == class_id,
        ClassTeacher.teacher_id == teacher_id,
    ).all()


def is_head_teacher(db: Session, class_id: int, teacher_id: int) -> bool:
    cls = db.get(Class, class_id)
    if cls is None:
        return False
    # classes.teacher_id 是存量班主任关系，新表启用后仍保持兼容。
    if cls.teacher_id == teacher_id:
        return True
    return any(row.role == "head_teacher" for row in class_teacher_scope(db, class_id, teacher_id))


def teacher_subjects(db: Session, class_id: int, teacher_id: int) -> set[str]:
    return {
        row.subject for row in class_teacher_scope(db, class_id, teacher_id)
        if row.role == "subject_teacher" and row.subject
    }


def require_case_access(
    db: Session,
    case_id: int,
    user: User,
    *,
    write: bool = False,
    subject: str = "",
) -> StudentCase:
    case = db.get(StudentCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="学生总案不存在")
    if user.role == ROLE_ADMIN:
        if write:
            raise HTTPException(status_code=403, detail="校长只能督查，不能修改班主任维护的总案")
        return case
    if user.role == ROLE_DEYU_DIRECTOR:
        if write:
            raise HTTPException(status_code=403, detail="德育主任只能审查，不能直接修改班主任维护的总案")
        return case
    if user.role == ROLE_PARENT:
        linked = db.query(StudentGuardian).filter_by(
            parent_id=user.id, student_id=case.student_id
        ).first()
        if write or linked is None or case.status not in PARENT_VISIBLE_STATUSES:
            raise HTTPException(status_code=403, detail="无权访问该学生总案")
        return case
    if user.role == ROLE_STUDENT:
        if write or case.student_id != user.id or case.status not in STUDENT_VISIBLE_STATUSES:
            raise HTTPException(status_code=403, detail="无权访问该学生总案")
        return case
    if user.role != ROLE_TEACHER:
        raise HTTPException(status_code=403, detail="无权访问该学生总案")
    if is_head_teacher(db, case.class_id, user.id):
        return case
    subjects = teacher_subjects(db, case.class_id, user.id)
    if not subjects or write:
        raise HTTPException(status_code=403, detail="学科教师可查看负责学科依据，正式内容由班主任维护")
    return case


def require_case_manager(db: Session, case: StudentCase, user: User) -> None:
    if user.role == ROLE_TEACHER and is_head_teacher(db, case.class_id, user.id):
        return
    raise HTTPException(status_code=403, detail="仅班主任可维护总案内容和过程记录")


def snapshot_payload(db: Session, case: StudentCase) -> dict[str, Any]:
    def columns(row):
        return {column.name: getattr(row, column.name) for column in row.__table__.columns}

    return jsonable_encoder({
        "case": columns(case),
        "student_profile": (
            columns(profile)
            if (profile := db.query(CaseStudentProfile).filter_by(student_case_id=case.id).first())
            else None
        ),
        "subject_plans": [columns(row) for row in db.query(SubjectPlan).filter_by(student_case_id=case.id)],
        "goals": [columns(row) for row in db.query(CaseGoal).filter_by(student_case_id=case.id)],
        "tasks": [columns(row) for row in db.query(CaseTask).filter_by(student_case_id=case.id)],
        "reviews": [columns(row) for row in db.query(CaseReview).filter_by(student_case_id=case.id)],
    })


def create_version(db: Session, case: StudentCase, actor_id: int, reason: str) -> CaseVersion:
    version = CaseVersion(
        student_case_id=case.id,
        version=case.version,
        snapshot=snapshot_payload(db, case),
        change_reason=reason,
        created_by=actor_id,
    )
    db.add(version)
    db.flush()
    return version


def audit(
    db: Session,
    actor_id: int,
    action: str,
    entity_type: str,
    entity_id: int | str = "",
    case_id: int | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    db.add(CaseAuditLog(
        student_case_id=case_id,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        detail=detail or {},
    ))


def transition_case(
    db: Session, case: StudentCase, target_status: str, actor: User, reason: str
) -> StudentCase:
    if target_status not in ALLOWED_TRANSITIONS.get(case.status, set()):
        raise HTTPException(
            status_code=409,
            detail=f"不允许从 {case.status} 流转到 {target_status}",
        )
    if target_status == CASE_STATUS_ADJUSTED:
        create_version(db, case, actor.id, reason or "阶段复盘调整")
        case.version += 1
    old_status = case.status
    case.status = target_status
    audit(
        db, actor.id, "case.transition", "student_case", case.id, case.id,
        {"from": old_status, "to": target_status, "reason": reason},
    )
    return case


def verify_case_membership(db: Session, student_id: int, class_id: int) -> None:
    member = db.query(ClassStudent).filter_by(
        class_id=class_id, student_id=student_id
    ).first()
    if member is None:
        raise HTTPException(status_code=409, detail="学生不属于所选班级")


def task_is_overdue(task: CaseTask) -> bool:
    return task.status not in {"completed", "cancelled"} and task.due_on < date.today()


def review_cutoff() -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=14)
