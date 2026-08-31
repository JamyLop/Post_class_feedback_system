"""班级管理 API：班级 CRUD 与学生名单维护。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.class_ import Class, ClassStudent
from app.models.user import ROLE_ADMIN, ROLE_STUDENT, ROLE_TEACHER, User
from app.core.security import hash_password

from app.schemas.class_ import (
    ClassCreate,
    ClassOut,
    ClassStudentOut,
    ClassUpdate,
    StudentAdd,
    StudentCreateAndEnroll,
    validate_class_category,
)

router = APIRouter(prefix="/classes", tags=["classes"])

_manager = require_roles([ROLE_ADMIN, ROLE_TEACHER])


def _check_class_owner(db: Session, class_id: int, user: User) -> Class:
    """校验班级存在且当前用户有权操作（教师仅限自己的班级）。"""
    cls = db.get(Class, class_id)
    if cls is None:
        raise HTTPException(status_code=404, detail="班级不存在")
    if user.role != ROLE_ADMIN and cls.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="无权操作该班级")
    return cls


@router.post("", response_model=ClassOut)
def create_class(
    body: ClassCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_manager),
):
    """创建班级（教师/管理员）。"""
    cls = Class(**body.model_dump(), teacher_id=user.id)
    db.add(cls)
    db.commit()
    db.refresh(cls)
    return cls


@router.get("", response_model=list[ClassOut])
def list_classes(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """班级列表：admin 全部、教师自己的、学生所在班级。"""
    if user.role == ROLE_ADMIN:
        return db.query(Class).order_by(Class.id.desc()).all()
    if user.role == ROLE_TEACHER:
        return (
            db.query(Class)
            .filter(Class.teacher_id == user.id)
            .order_by(Class.id.desc())
            .all()
        )
    # 学生：返回自己所在班级
    return (
        db.query(Class)
        .join(ClassStudent, ClassStudent.class_id == Class.id)
        .filter(ClassStudent.student_id == user.id)
        .order_by(Class.id.desc())
        .all()
    )


@router.get("/{class_id}", response_model=ClassOut)
def get_class(
    class_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cls = _check_class_owner(db, class_id, user)
    return cls


@router.put("/{class_id}", response_model=ClassOut)
def update_class(
    class_id: int,
    body: ClassUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(_manager),
):
    cls = _check_class_owner(db, class_id, user)
    changes = body.model_dump(exclude_unset=True)
    education_stage = changes.get("education_stage", cls.education_stage)
    grade = changes.get("grade", cls.grade)
    class_type = changes.get("class_type", cls.class_type)
    short_term_type = changes.get("short_term_type", cls.short_term_type)
    # 编辑时基于“现有值 + 本次改动”整体校验，不能只校验单个字段。
    try:
        validate_class_category(education_stage, grade, class_type, short_term_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if body.name is not None:
        cls.name = body.name
    if body.education_stage is not None:
        cls.education_stage = body.education_stage
    if body.grade is not None:
        cls.grade = body.grade
    if body.class_type is not None:
        cls.class_type = body.class_type
    if "short_term_type" in changes:
        cls.short_term_type = body.short_term_type
    if body.school_year is not None:
        cls.school_year = body.school_year
    db.commit()
    db.refresh(cls)
    return cls


@router.delete("/{class_id}")
def delete_class(
    class_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(_manager),
):
    """仅删除没有档案、作业或反馈数据的班级，避免级联丢失教学记录。"""
    from app.models.assignment import Assignment
    from app.models.feedback import FeedbackReport
    from app.models.student_case import StudentCase

    cls = _check_class_owner(db, class_id, user)
    blockers = []
    if db.query(StudentCase.id).filter_by(class_id=class_id).first():
        blockers.append("学生档案")
    if db.query(Assignment.id).filter_by(class_id=class_id).first():
        blockers.append("作业")
    if db.query(FeedbackReport.id).filter_by(class_id=class_id).first():
        blockers.append("反馈记录")
    if blockers:
        raise HTTPException(
            status_code=409,
            detail=f"该班级已关联{'、'.join(blockers)}，为防止数据丢失不能删除",
        )
    db.delete(cls)
    db.commit()
    return {"ok": True}


@router.post("/{class_id}/students", response_model=list[ClassStudentOut])
def add_students(
    class_id: int,
    body: StudentAdd,
    db: Session = Depends(get_db),
    user: User = Depends(_manager),
):
    """向班级批量添加学生（跳过非法/重复的 id）。"""
    _check_class_owner(db, class_id, user)
    added = []
    for sid in body.student_ids:
        stu = db.get(User, sid)
        if stu is None or stu.role != ROLE_STUDENT:
            continue
        exists = (
            db.query(ClassStudent)
            .filter(
                ClassStudent.class_id == class_id,
                ClassStudent.student_id == sid,
            )
            .first()
        )
        if exists:
            continue
        db.add(ClassStudent(class_id=class_id, student_id=sid))
        added.append(stu)
    db.commit()
    return added


def _ensure_user_profile_columns(db: Session) -> None:
    """兼容存量库：若 users 表缺少档案扩展列则在线补齐，避免额外迁移。"""
    try:
        from sqlalchemy import text

        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS gender VARCHAR(16) DEFAULT ''"))
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS ethnicity VARCHAR(32) DEFAULT ''"))
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS source_school VARCHAR(128) DEFAULT ''"))
        db.execute(text('ALTER TABLE users ADD COLUMN IF NOT EXISTS grade VARCHAR(32) DEFAULT \'\''))
        db.commit()
    except Exception:
        db.rollback()


def _generate_student_username(db: Session) -> str:
    import uuid

    for _ in range(20):
        cand = f"stu_{uuid.uuid4().hex[:8]}"
        if db.query(User).filter(User.username == cand).first() is None:
            return cand
    import random
    import time

    return f"stu_{int(time.time()) % 10000000:07d}{random.randint(10, 99)}"


@router.post("/{class_id}/students/create", response_model=ClassStudentOut)
def create_and_add_student(
    class_id: int,
    body: StudentCreateAndEnroll,
    db: Session = Depends(get_db),
    user: User = Depends(_manager),
):
    """在班级内直接新建学生账号并加入班级（仅录入档案信息，账号自动生成）。"""
    cls = _check_class_owner(db, class_id, user)
    _ensure_user_profile_columns(db)
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="姓名不能为空")
    username = _generate_student_username(db)
    # 默认初始密码 123456，班主任无需关心账号
    stu = User(
        username=username,
        password_hash=hash_password("123456"),
        name=name,
        role=ROLE_STUDENT,
        gender=(body.gender or "").strip(),
        ethnicity=(body.ethnicity or "").strip(),
        source_school=(body.source_school or "").strip(),
        grade=(body.grade or cls.grade or "").strip(),
    )
    db.add(stu)
    db.flush()
    db.add(ClassStudent(class_id=class_id, student_id=stu.id))
    db.commit()
    db.refresh(stu)
    return stu


@router.get("/{class_id}/students", response_model=list[ClassStudentOut])
def list_students(
    class_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cls = _check_class_owner(db, class_id, user)
    return (
        db.query(User)
        .join(ClassStudent, ClassStudent.student_id == User.id)
        .filter(ClassStudent.class_id == cls.id)
        .order_by(User.id.asc())
        .all()
    )
