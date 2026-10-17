"""历史初评任课姓名展示；解析结果不用于授权，也不写回历史方案。"""

from collections import defaultdict

from app.models.class_ import Class, ClassTeacher
from app.models.user import User
from app.schemas.student_case import SubjectPlanOut


def serialize_subject_plans(db, case, plans):
    teachers = {t.id: t for t in db.query(User).filter(User.id.in_({p.teacher_id for p in plans})).all()} if plans else {}
    cls = db.get(Class, case.class_id) if case.class_id else None
    assignments = defaultdict(set)
    if cls:
        for relation in db.query(ClassTeacher).filter_by(class_id=cls.id, role="subject_teacher").all():
            assignments[relation.subject].add(relation.teacher_id)
        ids = {tid for group in assignments.values() for tid in group}
        teachers.update({t.id: t for t in db.query(User).filter(User.id.in_(ids)).all()})
    result = []
    for plan in plans:
        teacher = teachers.get(plan.teacher_id)
        name = (plan.teacher_name or "").strip()
        # 旧导入以班主任占位。没有明确兼教关系时，不能把账号姓名当成授课老师。
        placeholder = bool(cls and case.owner_teacher_id == cls.teacher_id == plan.teacher_id
                           and plan.subject != "德育" and plan.teacher_id not in assignments[plan.subject])
        if placeholder and (not name or (teacher and name == teacher.name)):
            candidates = assignments[plan.subject]
            candidate = teachers.get(next(iter(candidates))) if len(candidates) == 1 else None
            name = candidate.name if candidate else "待确认任课老师"
        elif not name:
            name = teacher.name if teacher else "待确认任课老师"
        result.append({**SubjectPlanOut.model_validate(plan).model_dump(), "teacher_name": name})
    return result
