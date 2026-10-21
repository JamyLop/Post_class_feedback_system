"""学段主管只读范围，始终按班级的正式学段字段授权。"""
from fastapi import HTTPException

from app.models.class_ import Class
from app.models.user import ROLE_SUBJECT_TEACHER


def supervisor_stage(user):
    stage = user.supervisor_stage
    return stage if user.role == ROLE_SUBJECT_TEACHER and user.status == "active" and stage in {"初中", "高中"} else ""


def supervised_class_ids(db, user):
    stage = supervisor_stage(user)
    if not stage:
        raise HTTPException(status_code=403, detail="当前账号未获学段主管权限")
    return {row.id for row in db.query(Class.id).filter(Class.education_stage == stage).all()}


def can_supervise_class(db, user, class_id):
    stage = supervisor_stage(user)
    cls = db.get(Class, class_id) if stage and class_id is not None else None
    return bool(cls and cls.education_stage == stage)
