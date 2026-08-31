"""管理员控制台接口：系统概览 / 邀请码管理 / 用户删除。"""

import secrets
import string

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import require_roles
from app.core.database import get_db
from app.models.assignment import Assignment
from app.models.class_ import Class, StudentGuardian
from app.models.invite import (
    INVITE_STATUS_ACTIVE,
    INVITE_STATUS_DISABLED,
    InviteCode,
)
from app.models.submission import Submission
from app.models.user import (
    ROLE_ADMIN,
    ROLE_DEYU_DIRECTOR,
    ROLE_PARENT,
    ROLE_STUDENT,
    ROLE_TEACHER,
    ROLES,
    User,
)
from app.schemas.admin import (
    AdminStats,
    GuardianLinkCreate,
    GuardianLinkOut,
    InviteCodeCreate,
    InviteCodeOut,
)

router = APIRouter(prefix="/admin", tags=["admin"])

_admin_only = require_roles([ROLE_ADMIN])

_CODE_CHARS = string.ascii_uppercase + string.digits


def _generate_code(length: int = 8) -> str:
    """生成随机大写字母+数字邀请码。"""
    return "".join(secrets.choice(_CODE_CHARS) for _ in range(length))


@router.get("/stats", response_model=AdminStats)
def admin_stats(db: Session = Depends(get_db), admin: User = Depends(_admin_only)):
    """系统概览：各类账号与业务对象数量。"""
    counts = {}
    for role in ROLES:
        counts[role] = db.query(User).filter(User.role == role).count()
    return AdminStats(
        user_count=sum(counts.values()),
        admin_count=counts[ROLE_ADMIN],
        teacher_count=counts[ROLE_TEACHER],
        student_count=counts[ROLE_STUDENT],
        parent_count=counts[ROLE_PARENT],
        class_count=db.query(Class).count(),
        assignment_count=db.query(Assignment).count(),
        submission_count=db.query(Submission).count(),
    )


@router.post("/invite-codes", response_model=InviteCodeOut)
def create_invite_code(
    body: InviteCodeCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(_admin_only),
):
    """创建邀请码：支持班主任、德育主任、学生和家长，校长账号不开放自助注册。"""
    if body.role not in ROLES or body.role == ROLE_ADMIN:
        raise HTTPException(status_code=400, detail="邀请码角色必须是 teacher、deyu_director、student 或 parent")
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

    has_submissions = (
        db.query(Submission).filter(Submission.student_id == user_id).first()
        if target.role == ROLE_STUDENT
        else None
    )
    has_classes = (
        db.query(Class).filter(Class.teacher_id == user_id).first()
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
