"""用户管理 API：创建/查询/更新用户。

教师仅能管理学生角色账号，admin 可管理全部角色。
"""

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
    USER_STATUS_ACTIVE,
    USER_STATUS_DISABLED,
    User,
)
from app.schemas.user import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])

_manager = require_roles([ROLE_ADMIN, ROLE_TEACHER])


def _require_teacher_student_scope(actor: User, target_role: str) -> None:
    """教师只能创建和管理学生，不能读取或授予高权限角色。"""
    if actor.role == ROLE_TEACHER and target_role != ROLE_STUDENT:
        raise HTTPException(status_code=403, detail="教师仅可管理学生账号")


@router.post("", response_model=UserOut, dependencies=[Depends(_manager)])
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_manager),
):
    """创建用户（密码 bcrypt 加密存储）。"""
    if body.role not in ROLES:
        raise HTTPException(status_code=400, detail="无效角色")
    _require_teacher_student_scope(user, body.role)
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
    user: User = Depends(_manager),
):
    """按角色分页查询用户，支持用户名/姓名模糊搜索。"""
    if role not in ROLES:
        raise HTTPException(status_code=400, detail="无效角色")
    _require_teacher_student_scope(user, role)
    q = db.query(User).filter(User.role == role)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(
            User.username.ilike(like) | User.name.ilike(like)
        )
    return q.order_by(User.id.desc()).limit(200).all()


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(_manager),
):
    db_user = db.get(User, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    _require_teacher_student_scope(user, db_user.role)
    return db_user


@router.put("/{user_id}", response_model=UserOut, dependencies=[Depends(_manager)])
def update_user(
    user_id: int,
    body: UserUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(_manager),
):
    """更新用户：姓名/密码/状态（仅传入字段生效）。"""
    db_user = db.get(User, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    _require_teacher_student_scope(user, db_user.role)
    if body.name is not None:
        db_user.name = body.name
    if body.password is not None:
        db_user.password_hash = hash_password(body.password)
    if body.status is not None:
        if body.status not in (USER_STATUS_ACTIVE, USER_STATUS_DISABLED):
            raise HTTPException(status_code=400, detail="无效用户状态")
        db_user.status = body.status
    db.commit()
    db.refresh(db_user)
    return db_user
