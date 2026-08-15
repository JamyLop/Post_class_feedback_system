from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.invite import (
    INVITE_STATUS_ACTIVE,
    INVITE_STATUS_USED,
    InviteCode,
)
from app.models.user import ROLE_STUDENT, ROLE_TEACHER, User
from app.schemas.admin import RegisterRequest
from app.schemas.auth import LoginRequest, LoginResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if user.status != "active":
        raise HTTPException(status_code=403, detail="账号已被禁用")
    token = create_access_token(user.id, user.role)
    return LoginResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/register", response_model=UserOut)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """公开注册：角色仅限 teacher / student，必须携带未使用且在有效期内的邀请码。"""
    if body.role not in (ROLE_TEACHER, ROLE_STUDENT):
        raise HTTPException(status_code=400, detail="仅支持注册教师或学生账号")
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=409, detail="用户名已存在")

    invite = (
        db.query(InviteCode)
        .filter(InviteCode.code == body.invite_code.strip())
        .with_for_update()
        .first()
    )
    if invite is None:
        raise HTTPException(status_code=400, detail="邀请码不存在")
    if invite.role != body.role:
        raise HTTPException(status_code=400, detail="邀请码角色与所选角色不匹配")
    if invite.status != INVITE_STATUS_ACTIVE:
        raise HTTPException(status_code=400, detail="邀请码已被使用或停用")
    if invite.expires_at is not None and invite.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="邀请码已过期")

    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        name=body.name,
        role=body.role,
    )
    db.add(user)
    db.flush()

    invite.status = INVITE_STATUS_USED
    invite.used_by = user.id
    invite.used_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return user
