"""管理员控制台接口：系统概览 / 邀请码管理 / 用户删除。"""

import secrets
import string

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import require_roles
from app.core.database import get_db
from app.models.assignment import Assignment
from app.models.class_ import Class, StudentGuardian, StudentConsultant
from app.models.invite import (
    INVITE_STATUS_ACTIVE,
    INVITE_STATUS_DISABLED,
    InviteCode,
)
from app.models.submission import Submission
from app.models.user import (
    ROLE_ADMIN,
    ROLE_CONSULTANT,
    ROLE_DEYU_DIRECTOR,
    ROLE_PARENT,
    ROLE_STUDENT,
    ROLE_TEACHER,
    ROLES,
    User,
)
from sqlalchemy.exc import ProgrammingError

from app.schemas.admin import (
    AdminStats,
    GuardianLinkCreate,
    GuardianLinkOut,
    ConsultantLinkCreate,
    ConsultantLinkOut,
    InviteCodeCreate,
    InviteCodeOut,
)

router = APIRouter(prefix="/admin", tags=["admin"])

_admin_only = require_roles([ROLE_ADMIN])

_CODE_CHARS = string.ascii_uppercase + string.digits


def _safe_count(db: Session, model, fallback_model=None) -> int:
    """安全计数：兼容历史迁移已删除的 legacy 表（assignments/submissions 等）。

    若目标表不存在（ProgrammingError UndefinedTable），回滚事务并尝试 fallback 模型；
    否则返回 0，避免 500 导致校级概览页不可用。详见迁移 g1h2i3j4k5l6。
    """
    try:
        return db.query(model).count()
    except ProgrammingError:
        db.rollback()
        if fallback_model is not None:
            try:
                return db.query(fallback_model).count()
            except Exception:
                db.rollback()
                return 0
        return 0
    except Exception:
        db.rollback()
        return 0


def _generate_code(length: int = 8) -> str:
    """生成随机大写字母+数字邀请码。"""
    return "".join(secrets.choice(_CODE_CHARS) for _ in range(length))


@router.get("/stats", response_model=AdminStats)
def admin_stats(db: Session = Depends(get_db), admin: User = Depends(_admin_only)):
    """系统概览：各类账号与业务对象数量。"""
    counts = {}
    for role in ROLES:
        counts[role] = db.query(User).filter(User.role == role).count()
    # assignments / submissions 表已在 g1h2i3j4k5l6 中下线（被 student_case 体系替代），
    # 生产库查询会触发 UndefinedTable；用 _safe_count 兜底，避免 500。
    # 为保持前端契约，仍返回 assignment_count / submission_count，但底层回退到新域对象。
    from app.models.student_case import StudentCase

    from app.models.weekly_score import WeeklyTestScore

    return AdminStats(
        user_count=sum(counts.values()),
        admin_count=counts[ROLE_ADMIN],
        teacher_count=counts[ROLE_TEACHER],
        student_count=counts[ROLE_STUDENT],
        parent_count=counts[ROLE_PARENT],
        deyu_director_count=counts.get(ROLE_DEYU_DIRECTOR, 0),
        consultant_count=counts.get(ROLE_CONSULTANT, 0),
        class_count=_safe_count(db, Class),
        assignment_count=_safe_count(db, Assignment, fallback_model=StudentCase),
        submission_count=_safe_count(db, Submission, fallback_model=WeeklyTestScore),
        case_count=_safe_count(db, StudentCase),
    )


@router.post("/invite-codes", response_model=InviteCodeOut)
def create_invite_code(
    body: InviteCodeCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(_admin_only),
):
    """创建邀请码：支持班主任、德育主任、咨询老师、学生和家长，校长账号不开放自助注册。"""
    if body.role not in ROLES or body.role == ROLE_ADMIN:
        raise HTTPException(status_code=400, detail="邀请码角色必须是 teacher、deyu_director、consultant、student 或 parent")
    code = _generate_code()
    # 保证生成的邀请码在库中唯一
    while db.query(InviteCode).filter(InviteCode.code == code).first():
        code = _generate_code()
    invite = InviteCode(
        code=code,
        role=body.role,
        status=INVITE_STATUS_ACTIVE,
        created_by=admin.id,
        expires_at=body.expires_at,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return invite


@router.get("/invite-codes", response_model=list[InviteCodeOut])
def list_invite_codes(
    role: str = "",
    db: Session = Depends(get_db),
    admin: User = Depends(_admin_only),
):
    q = db.query(InviteCode)
    if role:
        q = q.filter(InviteCode.role == role)
    return q.order_by(InviteCode.id.desc()).limit(200).all()


@router.post("/invite-codes/{invite_id}/disable")
def disable_invite_code(
    invite_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(_admin_only),
):
    """停用邀请码（仅 active 状态可停用）。"""
    invite = db.get(InviteCode, invite_id)
    if invite is None:
        raise HTTPException(status_code=404, detail="邀请码不存在")
    if invite.status == INVITE_STATUS_ACTIVE:
        invite.status = INVITE_STATUS_DISABLED
        db.commit()
    return {"ok": True}


@router.get("/guardian-links", response_model=list[GuardianLinkOut])
def list_guardian_links(
    db: Session = Depends(get_db),
    admin: User = Depends(_admin_only),
):
    result = []
    for link in db.query(StudentGuardian).order_by(StudentGuardian.id.desc()).all():
        parent = db.get(User, link.parent_id)
        student = db.get(User, link.student_id)
        result.append({
            **GuardianLinkOut.model_validate(link).model_dump(),
            "parent_name": parent.name if parent else "",
            "student_name": student.name if student else "",
        })
    return result


@router.post("/guardian-links", response_model=GuardianLinkOut)
def create_guardian_link(
    body: GuardianLinkCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(_admin_only),
):
    parent = db.get(User, body.parent_id)
    student = db.get(User, body.student_id)
    if parent is None or parent.role != ROLE_PARENT:
        raise HTTPException(status_code=400, detail="所选账号不是家长")
    if student is None or student.role != ROLE_STUDENT:
        raise HTTPException(status_code=400, detail="所选账号不是学生")
    existing = db.query(StudentGuardian).filter_by(
        parent_id=body.parent_id, student_id=body.student_id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="该家长已关联此学生")
    link = StudentGuardian(**body.model_dump())
    db.add(link)
    db.commit()
    db.refresh(link)
    return {
        **GuardianLinkOut.model_validate(link).model_dump(),
        "parent_name": parent.name,
        "student_name": student.name,
    }


@router.delete("/guardian-links/{link_id}")
def delete_guardian_link(
    link_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(_admin_only),
):
    link = db.get(StudentGuardian, link_id)
    if link is None:
        raise HTTPException(status_code=404, detail="家长学生关系不存在")
    db.delete(link)
    db.commit()
    return {"ok": True}


def _consultant_out(db: Session, link: StudentConsultant) -> dict:
    consultant = db.get(User, link.consultant_id)
    student = db.get(User, link.student_id)
    return {
        **ConsultantLinkOut.model_validate(link).model_dump(),
        "consultant_name": consultant.name if consultant else "",
        "consultant_username": consultant.username if consultant else "",
        "student_name": student.name if student else "",
        "student_username": student.username if student else "",
    }


@router.get("/consultant-links", response_model=list[ConsultantLinkOut])
def list_consultant_links(db: Session = Depends(get_db), admin: User = Depends(_admin_only)):
    return [_consultant_out(db, link) for link in db.query(StudentConsultant).order_by(StudentConsultant.id.desc()).all()]


@router.post("/consultant-links", response_model=ConsultantLinkOut)
def create_consultant_link(body: ConsultantLinkCreate, db: Session = Depends(get_db), admin: User = Depends(_admin_only)):
    consultant = db.get(User, body.consultant_id)
    student = db.get(User, body.student_id)
    if consultant is None or consultant.role not in (ROLE_TEACHER, ROLE_CONSULTANT):
        raise HTTPException(status_code=400, detail="所选账号不是教师或咨询老师")
    if student is None or student.role != ROLE_STUDENT:
        raise HTTPException(status_code=400, detail="所选账号不是学生")
    if db.query(StudentConsultant).filter_by(consultant_id=body.consultant_id, student_id=body.student_id).first():
        raise HTTPException(status_code=409, detail="该咨询老师已关联此学生")
    link = StudentConsultant(**body.model_dump())
    db.add(link)
    db.commit()
    db.refresh(link)
    return _consultant_out(db, link)


@router.delete("/consultant-links/{link_id}")
def delete_consultant_link(link_id: int, db: Session = Depends(get_db), admin: User = Depends(_admin_only)):
    link = db.get(StudentConsultant, link_id)
    if link is None:
        raise HTTPException(status_code=404, detail="咨询老师与学生关系不存在")
    db.delete(link)
    db.commit()
    return {"ok": True}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(_admin_only),
):
    """删除用户。管理员不能删除自己；存在关联数据时返回 409 提示改用禁用。"""
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    if target.id == admin.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录账号")

    def _exists(query):
        try:
            return query.first()
        except ProgrammingError:
            db.rollback()
            return None
        except Exception:
            db.rollback()
            return None

    has_submissions = (
        _exists(db.query(Submission).filter(Submission.student_id == user_id))
        if target.role == ROLE_STUDENT
        else None
    )
    has_classes = (
        _exists(db.query(Class).filter(Class.teacher_id == user_id))
        if target.role == ROLE_TEACHER
        else None
    )
    has_invites = (
        db.query(InviteCode)
        .filter(
            (InviteCode.created_by == user_id) | (InviteCode.used_by == user_id)
        )
        .first()
    )
    if has_submissions is not None:
        raise HTTPException(status_code=409, detail="该学生存在提交记录，请改用禁用")
    if has_classes is not None:
        raise HTTPException(status_code=409, detail="该教师名下存在班级，请改用禁用")
    if has_invites is not None:
        raise HTTPException(status_code=409, detail="存在关联的邀请码记录，请改用禁用")

    db.delete(target)
    db.commit()
    return {"ok": True}
