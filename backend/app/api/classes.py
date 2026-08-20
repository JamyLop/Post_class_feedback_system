"""班级管理 API：班级 CRUD 与学生名单维护。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.class_ import Class, ClassStudent
from app.models.user import ROLE_ADMIN, ROLE_STUDENT, ROLE_TEACHER, User
from app.schemas.class_ import (
    ClassCreate,
    ClassOut,
    ClassStudentOut,
    ClassUpdate,
    StudentAdd,
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
    cls = Class(name=body.name, grade=body.grade, teacher_id=user.id)
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
    if body.name is not None:
        cls.name = body.name
    if body.grade is not None:
        cls.grade = body.grade
    db.commit()
    db.refresh(cls)
    return cls


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
