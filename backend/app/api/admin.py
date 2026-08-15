"""管理员控制台接口：系统概览 / 邀请码管理 / 用户删除。"""

import secrets
import string

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import require_roles
from app.core.database import get_db
from app.models.assignment import Assignment
from app.models.class_ import Class
from app.models.invite import (
    INVITE_STATUS_ACTIVE,
    INVITE_STATUS_DISABLED,
    InviteCode,
)
from app.models.submission import Submission
from app.models.user import (
    ROLE_ADMIN,
    ROLE_STUDENT,
    ROLE_TEACHER,
    ROLES,
    User,
)
from app.schemas.admin import AdminStats, InviteCodeCreate, InviteCodeOut

router = APIRouter(prefix="/admin", tags=["admin"])

_admin_only = require_roles([ROLE_ADMIN])

_CODE_CHARS = string.ascii_uppercase + string.digits


def _generate_code(length: int = 8) -> str:
    return "".join(secrets.choice(_CODE_CHARS) for _ in range(length))


@router.get("/stats", response_model=AdminStats)
def admin_stats(db: Session = Depends(get_db), admin: User = Depends(_admin_only)):
    counts = {}
    for role in ROLES:
        counts[role] = db.query(User).filter(User.role == role).count()
    return AdminStats(
        user_count=sum(counts.values()),
        admin_count=counts[ROLE_ADMIN],
        teacher_count=counts[ROLE_TEACHER],
        student_count=counts[ROLE_STUDENT],
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
    if body.role not in ROLES or body.role == ROLE_ADMIN:
        raise HTTPException(status_code=400, detail="邀请码角色必须是 teacher 或 student")
    code = _generate_code()
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
    invite = db.get(InviteCode, invite_id)
    if invite is None:
        raise HTTPException(status_code=404, detail="邀请码不存在")
    if invite.status == INVITE_STATUS_ACTIVE:
        invite.status = INVITE_STATUS_DISABLED
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