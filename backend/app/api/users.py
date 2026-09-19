"""用户管理 API：创建/查询/更新用户。

教师仅能管理学生角色账号，admin 可管理全部角色。
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.deps import require_roles
from app.core.database import get_db
from app.core.pagination import MAX_LIMIT, pagination_params
from app.core.security import hash_password
from app.models.user import (
    ROLE_ADMIN,
    ROLE_CONSULTANT,
    ROLE_DEYU_DIRECTOR,
    ROLE_STUDENT,
    ROLE_SUBJECT_TEACHER,
    ROLE_TEACHER,
    ROLES,
    USER_STATUS_ACTIVE,
    USER_STATUS_DISABLED,
    User,
)
from app.schemas.user import QuickStudentCreate, UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])

_manager = require_roles([ROLE_ADMIN, ROLE_TEACHER])
# 新建学生账号：班主任 + 咨询老师均可创建学生账号（仅限学生角色，见下方 scope 校验）。
_create_manager = require_roles([ROLE_ADMIN, ROLE_TEACHER, ROLE_CONSULTANT])
# 德育主任新建班级时需选择班主任，仅开放只读名单查询；创建/更新仍受角色范围限制。
# 咨询老师新建学生时需搜索已有学生，开放只读查询学生名单；其他角色仍不可见。
_list_manager = require_roles([ROLE_ADMIN, ROLE_TEACHER, ROLE_DEYU_DIRECTOR, ROLE_CONSULTANT])


def _require_teacher_student_scope(actor: User, target_role: str) -> None:
    """班主任/咨询老师只能创建和管理学生，不能读取或授予高权限角色。"""
    if actor.role in (ROLE_TEACHER, ROLE_CONSULTANT) and target_role != ROLE_STUDENT:
        raise HTTPException(status_code=403, detail="教师仅可管理学生账号")


def _require_phone_username_for_role(role: str, username: str) -> str:
    """除学生外，其他角色用户名必须为11位手机号。"""
    import re

    cleaned = (username or "").strip()
    if role != ROLE_STUDENT and not re.fullmatch(r"1[3-9]\d{9}", cleaned):
        raise HTTPException(status_code=400, detail="除学生外，用户名必须为11位手机号")
    return cleaned


@router.post("", response_model=UserOut, dependencies=[Depends(_create_manager)])
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_create_manager),
):
    """创建用户（密码 bcrypt 加密存储）。除学生外用户名必须为手机号。"""
    if body.role not in ROLES:
        raise HTTPException(status_code=400, detail="无效角色")
    _require_teacher_student_scope(user, body.role)
    body.username = _require_phone_username_for_role(body.role, body.username)
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=409, detail="用户名已存在")
    db_user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        name=body.name,
        role=body.role,
        channel=(body.channel or "").strip(),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.post("/quick-student", response_model=UserOut)
def quick_create_student(
    body: QuickStudentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_create_manager),
):
    """免班级快捷新建学生：仅录档案信息、不入班，账号自动生成。

    咨询老师新建时无需选择班级，学生先进“未分班池”并自动关联自己；
    后续班主任在班级学生名册用“选择已有学生”将其加入班级即可。
    """
    from app.models.class_ import StudentConsultant

    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="姓名不能为空")
    consultant = None
    if body.consultant_id is not None:
        consultant = db.get(User, body.consultant_id)
        if consultant is None or consultant.role not in (ROLE_TEACHER, ROLE_CONSULTANT):
            raise HTTPException(status_code=400, detail="所选咨询老师不存在")
    username = _generate_quick_student_username(db)
    # 默认初始密码 123456，与班级内新建学生保持一致
    stu = User(
        username=username,
        password_hash=hash_password("123456"),
        name=name,
        role=ROLE_STUDENT,
        gender=(body.gender or "").strip(),
        ethnicity=(body.ethnicity or "").strip(),
        source_school=(body.source_school or "").strip(),
        grade=(body.grade or "").strip(),
        channel=(body.channel or "").strip(),
    )
    db.add(stu)
    db.flush()
    if consultant is not None:
        db.add(StudentConsultant(consultant_id=consultant.id, student_id=stu.id))
    # 咨询老师新建默认关联自己，避免后续在咨询侧不可见
    if user.role == ROLE_CONSULTANT:
        exists_self = db.query(StudentConsultant).filter_by(
            consultant_id=user.id, student_id=stu.id
        ).first()
        if exists_self is None:
            db.add(StudentConsultant(consultant_id=user.id, student_id=stu.id))
    db.commit()
    db.refresh(stu)
    return stu


def _generate_quick_student_username(db: Session) -> str:
    """未分班学生临时学号：ZX + 年月(4位) + 序号(4位)，如 ZX26090001。

    入班后账号保持不变，班主任从已有学生中选择加入班级即可。
    """
    from datetime import date as _date

    prefix = f"ZX{_date.today().strftime('%y%m')}"
    seq = 1
    while True:
        username = f"{prefix}{seq:04d}"
        if db.query(User).filter(User.username == username).first() is None:
            return username
        seq += 1


@router.get("", response_model=list[UserOut])
def list_users(
    role: str = Query(default=ROLE_STUDENT),
    keyword: str = Query(default="", max_length=64),
    limit: int = Query(default=200, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(_list_manager),
):
    """按角色分页查询用户，支持用户名/姓名模糊搜索。"""
    if role not in ROLES:
        raise HTTPException(status_code=400, detail="无效角色")
    # 班主任新建学生时需选择咨询老师，允许只读查询 teacher/consultant 名单；
    # 德育主任排班和排课时需选择班主任、任课老师，允许只读查询两类名单；
    # 创建/更新仍受 _require_teacher_student_scope 限制。
    if user.role == ROLE_TEACHER and role in (ROLE_TEACHER, ROLE_CONSULTANT):
        pass
    elif user.role == ROLE_DEYU_DIRECTOR and role in (ROLE_TEACHER, ROLE_SUBJECT_TEACHER):
        pass
    else:
        _require_teacher_student_scope(user, role)
        if user.role == ROLE_DEYU_DIRECTOR:
            raise HTTPException(status_code=403, detail="德育主任仅可查询班主任名单")
    q = db.query(User).filter(User.role == role)
    if user.role == ROLE_CONSULTANT:
        # 咨询老师仅可见自己关联的学生（自己新建的会自动关联），避免看到全校学生名单
        from app.models.class_ import StudentConsultant

        linked_ids = [
            row.student_id
            for row in db.query(StudentConsultant).filter_by(consultant_id=user.id).all()
        ]
        q = q.filter(User.id.in_(linked_ids or [-1]))
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(
            User.username.ilike(like) | User.name.ilike(like)
        )
    return q.order_by(User.id.desc()).offset(offset).limit(limit).all()


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
    if body.channel is not None:
        db_user.channel = body.channel.strip()
    if body.password is not None:
        db_user.password_hash = hash_password(body.password)
    if body.status is not None:
        if body.status not in (USER_STATUS_ACTIVE, USER_STATUS_DISABLED):
            raise HTTPException(status_code=400, detail="无效用户状态")
        db_user.status = body.status
    db.commit()
    db.refresh(db_user)
    return db_user
