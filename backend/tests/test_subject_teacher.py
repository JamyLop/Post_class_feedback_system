"""任课老师角色验收：可见范围限定所带学科班级、只读方案、可提交学科建议。"""

from datetime import date, timedelta

from app.core.security import hash_password
from app.models.class_ import Class, ClassStudent, ClassTeacher
from app.models.user import ROLE_SUBJECT_TEACHER, User


def _setup_subject_scope(db, seed_users):
    """建班 + 学生 + 任课关系（subject1/数学）+ 另一个无关班级，返回 (class_id, other_class_id)。"""
    subject = User(
        username="subject1",
        password_hash=hash_password("test123456"),
        name="李老师",
        role=ROLE_SUBJECT_TEACHER,
    )
    db.add(subject)
    db.flush()
    cls = Class(
        name="高二(1)班",
        grade="高二",
        school_year_starts_on=date(2025, 9, 1),
        teacher_id=seed_users["teacher1"],
    )
    other = Class(
        name="高二(2)班",
        grade="高二",
        school_year_starts_on=date(2025, 9, 1),
        teacher_id=seed_users["teacher2"],
    )
    db.add_all([cls, other])
    db.flush()
    db.add_all([
        ClassStudent(class_id=cls.id, student_id=seed_users["student1"]),
        ClassStudent(class_id=other.id, student_id=seed_users["student2"]),
        ClassTeacher(
            class_id=cls.id,
            teacher_id=subject.id,
            role="subject_teacher",
            subject="数学",
        ),
    ])
    db.commit()
    return cls.id, other.id


def _create_cycle_and_cases(client, auth, class_id, other_class_id, seed_users):
    cycle = client.post(
        "/api/student-cases/cycles",
        headers=auth("admin"),
        json={
            "name": "2026学年",
            "school_year": "2026-2027",
            "starts_on": str(date.today()),
            "ends_on": str(date.today() + timedelta(days=180)),
        },
    )
    assert cycle.status_code == 200, cycle.text
    cycle_id = cycle.json()["id"]
    base = {
        "cycle_id": cycle_id,
        "owner_teacher_id": seed_users["teacher1"],
        "overall_problem": "基础待加强",
        "admission_target": "本科",
        "current_summary": "首轮复习",
    }
    case = client.post(
        "/api/student-cases",
        headers=auth("teacher1"),
        json={**base, "student_id": seed_users["student1"], "class_id": class_id},
    )
    assert case.status_code == 200, case.text
    # 无关班级的档案由 teacher2 建立（teacher2 需先成为该班班主任：Class.teacher_id 已是 teacher2）
    other_case = client.post(
        "/api/student-cases",
        headers=auth("teacher2"),
        json={
            **base,
            "owner_teacher_id": seed_users["teacher2"],
            "student_id": seed_users["student2"],
            "class_id": other_class_id,
        },
    )
    assert other_case.status_code == 200, other_case.text
    return cycle_id, case.json()["id"], other_case.json()["id"]


def _make_plans(client, auth, case_id, seed_users):
    for subject in ("数学", "英语"):
        r = client.put(
            f"/api/student-cases/{case_id}/subject-plans/{subject}",
            headers=auth("teacher1"),
            json={
                "subject": subject,
                "teacher_id": seed_users["teacher1"],
                "teacher_name": "王老师",
                "problem_location": f"{subject}待加强",
            },
        )
        assert r.status_code == 200, r.text


def test_subject_teacher_list_scoped_to_own_classes(client, auth, db, seed_users):
    class_id, other_class_id = _setup_subject_scope(db, seed_users)
    _, case_id, other_case_id = _create_cycle_and_cases(client, auth, class_id, other_class_id, seed_users)
    r = client.get("/api/student-cases", headers=auth("subject1"))
    assert r.status_code == 200, r.text
    ids = {row["id"] for row in r.json()}
    assert case_id in ids
    assert other_case_id not in ids


def test_subject_teacher_detail_sees_only_own_subject_plans(client, auth, db, seed_users):
    class_id, other_class_id = _setup_subject_scope(db, seed_users)
    _, case_id, _ = _create_cycle_and_cases(client, auth, class_id, other_class_id, seed_users)
    _make_plans(client, auth, case_id, seed_users)
    r = client.get(f"/api/student-cases/{case_id}", headers=auth("subject1"))
    assert r.status_code == 200, r.text
    subjects = {plan["subject"] for plan in r.json()["subject_plans"]}
    assert subjects == {"数学"}
    # 无关班级档案不可见
    r = client.get("/api/student-cases", headers=auth("subject1"))
    assert all(row["class_id"] == class_id for row in r.json())


def test_subject_teacher_suggestion_flow(client, auth, db, seed_users):
    class_id, other_class_id = _setup_subject_scope(db, seed_users)
    _, case_id, _ = _create_cycle_and_cases(client, auth, class_id, other_class_id, seed_users)
    # 本学科建议可提交
    r = client.post(
        f"/api/student-cases/{case_id}/subject-suggestions",
        headers=auth("subject1"),
        json={"subject": "数学", "content": "建议加强函数图像训练"},
    )
    assert r.status_code == 200, r.text
    # 非所带学科拒绝
    r = client.post(
        f"/api/student-cases/{case_id}/subject-suggestions",
        headers=auth("subject1"),
        json={"subject": "英语", "content": "越界建议"},
    )
    assert r.status_code == 403
    # 只能看到自己的建议
    r = client.get(f"/api/student-cases/{case_id}/subject-suggestions", headers=auth("subject1"))
    assert r.status_code == 200, r.text
    subject = db.query(User).filter(User.username == "subject1").first()
    assert r.json(), "应能看到自己提交的建议"
    assert {s["teacher_id"] for s in r.json()} == {subject.id}


def test_subject_teacher_cannot_write_plans_or_cases(client, auth, db, seed_users):
    class_id, other_class_id = _setup_subject_scope(db, seed_users)
    cycle_id, case_id, _ = _create_cycle_and_cases(client, auth, class_id, other_class_id, seed_users)
    # 不能直接修改学科方案
    r = client.put(
        f"/api/student-cases/{case_id}/subject-plans/数学",
        headers=auth("subject1"),
        json={"subject": "数学", "teacher_id": seed_users["teacher1"], "problem_location": "越权修改"},
    )
    assert r.status_code == 403
    # 不能新建总案
    r = client.post(
        "/api/student-cases",
        headers=auth("subject1"),
        json={
            "cycle_id": cycle_id,
            "student_id": seed_users["student2"],
            "class_id": class_id,
            "owner_teacher_id": seed_users["teacher1"],
        },
    )
    assert r.status_code == 403


def test_subject_teacher_register_with_invite(client, auth, db, seed_users):
    r = client.post(
        "/api/admin/invite-codes",
        headers=auth("admin"),
        json={"role": "subject_teacher"},
    )
    assert r.status_code == 200, r.text
    code = r.json()["code"]
    r = client.post(
        "/api/auth/register",
        json={
            "username": "subject_new",
            "password": "test123456",
            "name": "新任课老师",
            "role": "subject_teacher",
            "subject": "数学",
            "invite_code": code,
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "subject_teacher"
    assert db.query(User).filter_by(username="subject_new").one().subject == "数学"


def test_admin_class_teacher_links_crud(client, auth, db, seed_users):
    class_id, _ = _setup_subject_scope(db, seed_users)
    # 非管理员不可访问
    r = client.get("/api/admin/class-teacher-links", headers=auth("teacher1"))
    assert r.status_code == 403
    # 管理员可查看
    r = client.get("/api/admin/class-teacher-links", headers=auth("admin"))
    assert r.status_code == 200, r.text
    assert any(link["subject"] == "数学" for link in r.json())
    # 重复分配冲突
    subject = db.query(User).filter(User.username == "subject1").first()
    r = client.post(
        "/api/admin/class-teacher-links",
        headers=auth("admin"),
        json={"class_id": class_id, "teacher_id": subject.id, "subject": "数学"},
    )
    assert r.status_code == 409
    # 非任课老师账号拒绝
    r = client.post(
        "/api/admin/class-teacher-links",
        headers=auth("admin"),
        json={"class_id": class_id, "teacher_id": seed_users["student1"], "subject": "数学"},
    )
    assert r.status_code == 400
