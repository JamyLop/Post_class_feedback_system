from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.deps import require_roles
from app.core.database import get_db
from app.core.security import hash_password
from app.models.user import (
    ROLE_ADMIN,
    ROLE_STUDENT,
    ROLE_TEACHER,
    ROLES,
    User,
)
from app.schemas.user import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])

_manager = require_roles([ROLE_ADMIN, ROLE_TEACHER])


@router.post("", response_model=UserOut, dependencies=[Depends(_manager)])
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_manager),
):
    if body.role not in ROLES:
        raise HTTPException(status_code=400, detail="无效角色")
    if body.role == ROLE_TEACHER and user.role != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="仅管理员可创建教师账号")
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=409, detail="用户名已存在")
    db_user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        name=body.name,
        role=body.role,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.get("", response_model=list[UserOut], dependencies=[Depends(_manager)])
def list_users(
    role: str = Query(default=ROLE_STUDENT),
    keyword: str = Query(default="", max_length=64),
    db: Session = Depends(get_db),
):
    q = db.query(User).filter(User.role == role)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(
            User.username.ilike(like) | User.name.ilike(like)
        )
    return q.order_by(User.id.desc()).limit(200).all()


@router.get("/{user_id}", response_model=UserOut, dependencies=[Depends(_manager)])
def get_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.get(User, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return db_user


@router.put("/{user_id}", response_model=UserOut, dependencies=[Depends(_manager)])
def update_user(
    user_id: int,
    body: UserUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(_manager),
):
    db_user = db.get(User, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    if db_user.role == ROLE_TEACHER and user.role != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="仅管理员可管理教师账号")
    if body.name is not None:
        db_user.name = body.name
    if body.password is not None:
        db_user.password_hash = hash_password(body.password)
    if body.status is not None:
        if db_user.role == ROLE_TEACHER and user.role != ROLE_ADMIN:
            raise HTTPException(status_code=403, detail="仅管理员可管理教师账号")
        db_user.status = body.status
    db.commit()
    db.refresh(db_user)
    return db_user
