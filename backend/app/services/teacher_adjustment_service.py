"""班级学科换师：交接在用方案的负责人，保留内容和历史署名。"""

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.class_ import Class, ClassTeacher
from app.models.student_case import CaseCycle, StudentCase, SubjectPlan
from app.models.user import ROLE_SUBJECT_TEACHER, ROLE_TEACHER, User
from app.schemas.admin import ClassTeacherLinkAdjustment
from app.services.student_case_service import audit


def adjust_class_teacher(
    db: Session, link_id: int, body: ClassTeacherLinkAdjustment, actor: User,
) -> tuple[ClassTeacher, int]:
    teacher = db.query(User).filter_by(id=body.teacher_id).with_for_update().first()
    if teacher is None or teacher.role not in {ROLE_SUBJECT_TEACHER, ROLE_TEACHER} or teacher.status != "active":
        raise HTTPException(400, "请选择已启用的任课老师或兼课班主任")
    current = db.get(ClassTeacher, link_id)
    if current is None:
        raise HTTPException(404, "任课关系不存在")
    # 与调班保持班级、档案、方案的锁顺序，交接不能与学生调班交错写入。
    if db.query(Class).filter_by(id=current.class_id).with_for_update().first() is None:
        raise HTTPException(404, "班级不存在")
    link = db.query(ClassTeacher).filter_by(id=link_id).populate_existing().with_for_update().first()
    if link is None:
        raise HTTPException(404, "任课关系不存在")
    if link.role != "subject_teacher" or not link.subject.strip() or link.subject.strip() == "德育":
        raise HTTPException(400, "仅支持调整具体学科的任课老师，德育由班主任维护")
    if link.teacher_id != body.previous_teacher_id:
        raise HTTPException(409, "任课老师已被调整，请刷新列表后重试")
    if link.teacher_id == teacher.id:
        raise HTTPException(400, "请选择与原任课老师不同的接任老师")
    if db.query(ClassTeacher).filter_by(class_id=link.class_id, subject=link.subject, teacher_id=teacher.id).first():
        raise HTTPException(409, "接任老师已关联此班级此学科，请核对任课关联")

    cases = db.query(StudentCase).join(CaseCycle, CaseCycle.id == StudentCase.cycle_id).filter(
        StudentCase.class_id == link.class_id,
        StudentCase.status != "archived", CaseCycle.is_active.is_(True),
    ).order_by(StudentCase.id).populate_existing().with_for_update(of=StudentCase).all()
    # 仅交接该条关联原老师名下的在用方案；其他老师、已归档和停用周期保持原归属。
    plans = db.query(SubjectPlan).filter(
        SubjectPlan.student_case_id.in_([case.id for case in cases]),
        SubjectPlan.subject == link.subject,
        SubjectPlan.teacher_id == link.teacher_id,
    ).order_by(SubjectPlan.id).populate_existing().with_for_update().all()
    previous_id = link.teacher_id
    detail = dict(class_id=link.class_id, subject=link.subject, previous_teacher_id=previous_id,
                  teacher_id=teacher.id, reason=body.reason.strip())
    link.teacher_id = teacher.id
    for plan in plans:
        plan.teacher_id, plan.teacher_name = teacher.id, teacher.name
        # 复用分配事件，Web 和小程序现有待办会随负责人一起交接。
        audit(db, actor.id, "subject_plan.assigned", "subject_plan", plan.id,
              plan.student_case_id, {**detail, "source": "class_teacher.adjusted", "link_id": link.id})
    audit(db, actor.id, "class_teacher.adjusted", "class_teacher", link.id,
          detail={**detail, "updated_plans": len(plans), "plan_ids": [plan.id for plan in plans]})
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "任课关联发生变化，请刷新列表后重试")
    db.refresh(link)
    return link, len(plans)
