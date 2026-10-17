"""初评姓名展示不把班主任占位 ID 误当成任课老师，也不修改授权数据。"""
from datetime import date

from app.models.class_ import Class, ClassStudent, ClassTeacher
from app.models.student_case import CaseCycle, StudentCase, SubjectPlan
from app.models.user import User


def test_initial_plan_names_resolve_without_rewriting_teacher_ids(client, auth, db, seed_users):
    head = db.get(User, seed_users["teacher1"])
    teacher = db.get(User, seed_users["teacher2"])
    other = User(username="display_other", name="另一名任课老师", role="subject_teacher", password_hash="unused")
    cls = Class(name="初评姓名验证班", grade="高三", teacher_id=head.id)
    cycle = CaseCycle(name="初评验证周期", grade="高三", school_year="2026", starts_on=date(2026, 9, 1), ends_on=date(2027, 7, 1))
    db.add_all([other, cls, cycle])
    db.flush()
    case = StudentCase(student_id=seed_users["student1"], class_id=cls.id, cycle_id=cycle.id, owner_teacher_id=head.id)
    db.add(case)
    db.add(ClassStudent(student_id=seed_users["student1"], class_id=cls.id))
    db.flush()
    plans=[]
    for subject in ("语文", "数学", "英语", "政治", "历史", "地理", "德育", "物理"):
        plan=SubjectPlan(student_case_id=case.id, subject=subject, teacher_id=teacher.id if subject=="数学" else head.id,
                         teacher_name="手填任课老师" if subject=="英语" else head.name if subject=="物理" else "", problem_location="原始初评内容")
        db.add(plan)
        plans.append(plan)
    for subject, tid in (("语文",teacher.id),("历史",head.id),("地理",teacher.id),("地理",other.id),("物理",teacher.id)):
        db.add(ClassTeacher(class_id=cls.id,teacher_id=tid,role="subject_teacher",subject=subject))
    db.commit()
    before={p.id:(p.teacher_id,p.teacher_name,p.problem_location) for p in plans}
    response=client.get(f"/api/student-cases/{case.id}",headers=auth("teacher1"))
    assert response.status_code==200,response.text
    rows={p["subject"]:p for p in response.json()["subject_plans"]}
    assert {subject:row["teacher_name"] for subject,row in rows.items()}=={
        "语文":teacher.name,"数学":teacher.name,"英语":"手填任课老师","政治":"待确认任课老师",
        "历史":head.name,"地理":"待确认任课老师","德育":head.name,"物理":teacher.name,
    }
    assert rows["语文"]["teacher_id"]==head.id
    for plan in plans:
        db.refresh(plan)
        assert (plan.teacher_id,plan.teacher_name,plan.problem_location)==before[plan.id]
    assert client.get(f"/api/student-cases/{case.id}",headers=auth("student2")).status_code==403
