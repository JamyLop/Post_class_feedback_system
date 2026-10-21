"""任课老师角色验收：班级可见范围、分配初评填写、学科建议与权限边界。"""

from datetime import date, timedelta

from app.core.security import hash_password
from app.models.class_ import Class, ClassStudent, ClassTeacher
from app.models.user import ROLE_SUBJECT_TEACHER, User
from app.models.student_case import CaseAuditLog, StudentCase, SubjectPlan


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


def test_plan_teacher_name_resolves_real_account_and_class_scope(client, auth, db, seed_users):
    class_id, other_class_id = _setup_subject_scope(db, seed_users)
    _, case_id, other_case_id = _create_cycle_and_cases(client, auth, class_id, other_class_id, seed_users)
    subject_teacher = db.query(User).filter_by(username="subject1").one()
    db.query(ClassTeacher).filter_by(teacher_id=subject_teacher.id).delete()
    db.commit()
    response = client.put(
        f"/api/student-cases/{case_id}/subject-plans/数学",
        headers=auth("teacher1"),
        json={"subject": "数学", "teacher_id": seed_users["teacher1"], "teacher_name": "李老师"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["teacher_id"] == subject_teacher.id
    assert db.query(ClassTeacher).filter_by(class_id=class_id, teacher_id=seed_users["teacher1"]).count() == 0
    classes = client.get("/api/classes", headers=auth("subject1"))
    assert {row["id"] for row in classes.json()} == {class_id}
    students = client.get(f"/api/classes/{class_id}/students", headers=auth("subject1"))
    assert students.status_code == 200
    assert {row["id"] for row in students.json()} == {seed_users["student1"]}
    cases = client.get("/api/student-cases", headers=auth("subject1"))
    assert {row["id"] for row in cases.json()} == {case_id}
    assert client.get(f"/api/student-cases/{other_case_id}", headers=auth("subject1")).status_code == 403
    # 旧版小程序再次保存不能把已修复的任课归属写回班主任。
    response = client.put(
        f"/api/student-cases/{case_id}/subject-plans/数学",
        headers=auth("teacher1"),
        json={"subject": "数学", "teacher_id": seed_users["teacher1"], "reinforcement": "更新措施"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["teacher_id"] == subject_teacher.id
    assert response.json()["teacher_name"] == "李老师"


def test_manual_teacher_name_does_not_grant_head_teacher_subject_scope(client, auth, db, seed_users):
    class_id, other_class_id = _setup_subject_scope(db, seed_users)
    _, case_id, _ = _create_cycle_and_cases(client, auth, class_id, other_class_id, seed_users)
    response = client.put(
        f"/api/student-cases/{case_id}/subject-plans/英语",
        headers=auth("teacher1"),
        json={"subject": "英语", "teacher_id": seed_users["teacher1"], "teacher_name": "尚未注册的老师"},
    )
    assert response.status_code == 200, response.text
    assert db.query(ClassTeacher).filter_by(class_id=class_id, teacher_id=seed_users["teacher1"]).count() == 0


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


def test_initial_assignment_and_subject_teacher_filling(client, auth, db, seed_users):
    class_id, other_class_id = _setup_subject_scope(db, seed_users)
    _, case_id, other_case_id = _create_cycle_and_cases(client, auth, class_id, other_class_id, seed_users)
    teacher = db.query(User).filter_by(username="subject1").one()
    url = f"/api/student-cases/{case_id}/subject-plans/数学"
    manager_headers, teacher_headers = auth("teacher1"), auth("subject1")
    detail = client.get(f"/api/student-cases/{case_id}", headers=manager_headers).json()
    assert detail["can_assign_subjects"] is True
    assert detail["subject_teacher_options"] == [{"subject": "数学", "teacher_id": teacher.id, "teacher_name": teacher.name}]
    # 班级任课关系不允许自领；班主任可直接建立空白科目并分配。
    body = {"subject": "数学", "teacher_id": teacher.id, "problem_location": "函数基础薄弱"}
    assert client.put(url, headers=teacher_headers, json=body).status_code == 403
    assigned = client.put(url + "/assignment", headers=manager_headers, json={"teacher_id": teacher.id})
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["problem_location"] == ""
    detail = client.get(f"/api/student-cases/{case_id}", headers=teacher_headers).json()
    assert detail["can_manage"] is False
    assert detail["can_assign_subjects"] is False
    assert detail["subject_teacher_options"] == []
    assert detail["editable_subjects"] == ["数学"]
    response = client.put(url, headers=teacher_headers, json=body)
    assert response.status_code == 200, response.text
    assert response.json()["problem_location"] == "函数基础薄弱"
    # 任课老师不能跨科、改派、改总案或修改任务。
    assert client.put(url.replace("数学", "英语"), headers=teacher_headers, json={**body, "subject": "英语"}).status_code == 403
    assert client.put(url, headers=teacher_headers, json={**body, "teacher_id": seed_users["teacher1"]}).status_code == 403
    assert client.put(url, headers=teacher_headers, json={**body, "teacher_name": "其他老师"}).status_code == 403
    assert client.put(url + "/assignment", headers=teacher_headers, json={"teacher_id": teacher.id}).status_code == 403
    assert client.patch(f"/api/student-cases/{case_id}", headers=teacher_headers, json={"overall_problem": "越权"}).status_code == 403
    assert client.put(f"/api/student-cases/{other_case_id}/subject-plans/数学", headers=teacher_headers, json=body).status_code == 403
    log = db.query(CaseAuditLog).filter_by(action="subject_plan.assigned", student_case_id=case_id).one()
    assert log.detail == {"subject": "数学", "previous_teacher_id": None, "teacher_id": teacher.id}


def test_initial_reassignment_preserves_content_and_revokes_previous_writer(client, auth, db, seed_users):
    class_id, other_class_id = _setup_subject_scope(db, seed_users)
    _, case_id, _ = _create_cycle_and_cases(client, auth, class_id, other_class_id, seed_users)
    teacher = db.query(User).filter_by(username="subject1").one()
    # 兼任其他班班主任的老师也可以承担本班数学；同名不影响按账号分配。
    db.add(ClassTeacher(class_id=class_id, teacher_id=seed_users["teacher2"], role="subject_teacher", subject="数学"))
    db.commit()
    url = f"/api/student-cases/{case_id}/subject-plans/数学"
    manager_headers, teacher_headers = auth("teacher1"), auth("subject1")
    assert client.put(url + "/assignment", headers=manager_headers, json={"teacher_id": teacher.id}).status_code == 200
    content = {"subject": "数学", "teacher_id": teacher.id, "problem_location": "原始问题", "reinforcement": "原始措施"}
    assert client.put(url, headers=teacher_headers, json=content).status_code == 200
    response = client.put(url + "/assignment", headers=manager_headers, json={"teacher_id": seed_users["teacher2"]})
    assert response.status_code == 200, response.text
    assert response.json()["problem_location"] == "原始问题"
    assert response.json()["reinforcement"] == "原始措施"
    # 班主任后续核对保存，也不能把同名的兼课账号反查成另一个老师。
    response = client.put(url, headers=manager_headers, json={**content, "teacher_id": seed_users["teacher2"], "teacher_name": teacher.name})
    assert response.status_code == 200, response.text
    assert response.json()["teacher_id"] == seed_users["teacher2"]
    assert client.put(url, headers=teacher_headers, json=content).status_code == 403
    assert client.get(f"/api/student-cases/{case_id}", headers=teacher_headers).json()["editable_subjects"] == []
    new_headers = auth("teacher2")
    assert client.get(f"/api/student-cases/{case_id}", headers=new_headers).json()["editable_subjects"] == ["数学"]
    response = client.put(url, headers=new_headers, json={**content, "teacher_id": seed_users["teacher2"], "reinforcement": "兼课老师填写"})
    assert response.status_code == 200, response.text
    assert response.json()["teacher_id"] == seed_users["teacher2"]


def test_initial_assignment_rejects_wrong_subject_class_disabled_and_roles(client, auth, db, seed_users):
    class_id, other_class_id = _setup_subject_scope(db, seed_users)
    _, case_id, _ = _create_cycle_and_cases(client, auth, class_id, other_class_id, seed_users)
    teacher = db.query(User).filter_by(username="subject1").one()
    url = f"/api/student-cases/{case_id}/subject-plans"
    headers = auth("teacher1")
    for subject, teacher_id in [("英语", teacher.id), ("德育", teacher.id), ("数学", seed_users["teacher2"]), ("数学", seed_users["student1"]), ("数学", 999999)]:
        response = client.put(f"{url}/{subject}/assignment", headers=headers, json={"teacher_id": teacher_id})
        assert response.status_code == 400, response.text
    assert client.put(f"{url}/数学/assignment", headers=auth("teacher2"), json={"teacher_id": teacher.id}).status_code == 403
    assert client.put(f"{url}/数学/assignment", headers=auth("admin"), json={"teacher_id": teacher.id}).status_code == 403
    teacher.status = "disabled"
    db.commit()
    assert client.get(f"/api/student-cases/{case_id}", headers=headers).json()["subject_teacher_options"] == []
    assert client.put(f"{url}/数学/assignment", headers=headers, json={"teacher_id": teacher.id}).status_code == 400
    assert db.query(SubjectPlan).filter_by(student_case_id=case_id).count() == 0


def test_initial_filling_and_assignment_respect_review_locks(client, auth, db, seed_users):
    class_id, other_class_id = _setup_subject_scope(db, seed_users)
    _, case_id, _ = _create_cycle_and_cases(client, auth, class_id, other_class_id, seed_users)
    teacher = db.query(User).filter_by(username="subject1").one()
    manager_headers, teacher_headers = auth("teacher1"), auth("subject1")
    url = f"/api/student-cases/{case_id}/subject-plans/数学"
    assert client.put(url + "/assignment", headers=manager_headers, json={"teacher_id": teacher.id}).status_code == 200
    case = db.get(StudentCase, case_id)
    for status in ["pending_confirmation", "executing", "adjusted", "archived", "revision_required", "pending_review"]:
        case.status = status
        db.commit()
        writable = status in {"revision_required", "pending_review"}
        response = client.put(url, headers=teacher_headers, json={"subject": "数学", "teacher_id": teacher.id, "problem_location": "新问题"})
        assert response.status_code == (200 if writable else 409), response.text
        response = client.put(url + "/assignment", headers=manager_headers, json={"teacher_id": teacher.id})
        assert response.status_code == (200 if writable else 409), response.text
        detail = client.get(f"/api/student-cases/{case_id}", headers=teacher_headers).json()
        assert detail["editable_subjects"] == (["数学"] if writable else [])


def test_assignment_reminder_persists_until_assignee_saves_content(client, auth, db, seed_users):
    class_id, other_class_id = _setup_subject_scope(db, seed_users)
    _, case_id, _ = _create_cycle_and_cases(client, auth, class_id, other_class_id, seed_users)
    teacher = db.query(User).filter_by(username="subject1").one()
    manager, assignee = auth("teacher1"), auth("subject1")
    url = f"/api/student-cases/{case_id}/subject-plans/数学"
    reminders = "/api/student-cases/subject-plan-reminders"
    assert client.get(reminders, headers=assignee).json() == {"total": 0, "items": []}
    for _ in range(2):
        assert client.put(url + "/assignment", headers=manager, json={"teacher_id": teacher.id}).status_code == 200
    result = client.get(reminders, headers=assignee).json()
    assert result["total"] == len(result["items"]) == 1
    assert result["items"][0] == {
        "plan_id": db.query(SubjectPlan).filter_by(student_case_id=case_id).one().id,
        "case_id": case_id, "student_name": "张三", "class_name": "高二(1)班", "subject": "数学",
    }
    assert client.get(reminders, headers=auth("teacher2")).json()["total"] == 0
    # 阅读、空白保存、班主任代改都不能冒充本人的填写。
    client.get(f"/api/student-cases/{case_id}", headers=assignee)
    body = {"subject": "数学", "teacher_id": teacher.id, "teacher_name": teacher.name}
    assert client.put(url, headers=assignee, json={**body, "problem_location": "   "}).status_code == 200
    assert client.get(reminders, headers=assignee).json()["total"] == 1
    # 空白保存之后即使班主任补写，也仍需要本人处理。
    assert client.put(url, headers=manager, json={**body, "problem_location": "班主任补充"}).status_code == 200
    assert client.get(reminders, headers=assignee).json()["total"] == 1
    assert client.put(url, headers=assignee, json={**body, "reinforcement": "每天练习"}).status_code == 200
    assert client.get(reminders, headers=assignee).json() == {"total": 0, "items": []}


def test_assignment_reminder_reassignment_and_editable_status_scope(client, auth, db, seed_users):
    class_id, other_class_id = _setup_subject_scope(db, seed_users)
    _, case_id, _ = _create_cycle_and_cases(client, auth, class_id, other_class_id, seed_users)
    teacher = db.query(User).filter_by(username="subject1").one()
    db.add(ClassTeacher(class_id=class_id, teacher_id=seed_users["teacher2"], role="subject_teacher", subject="数学"))
    db.commit()
    manager, old, new = auth("teacher1"), auth("subject1"), auth("teacher2")
    url = f"/api/student-cases/{case_id}/subject-plans/数学"
    reminders = "/api/student-cases/subject-plan-reminders"
    assert client.put(url + "/assignment", headers=manager, json={"teacher_id": teacher.id}).status_code == 200
    assert client.put(url, headers=old, json={"subject": "数学", "teacher_id": teacher.id, "reinforcement": "原始内容"}).status_code == 200
    assert client.put(url + "/assignment", headers=manager, json={"teacher_id": seed_users["teacher2"]}).status_code == 200
    assert client.get(reminders, headers=old).json()["total"] == 0
    assert client.get(reminders, headers=new).json()["total"] == 1
    case = db.get(StudentCase, case_id)
    for status in ["pending_confirmation", "executing", "adjusted", "archived", "revision_required", "pending_review"]:
        case.status = status
        db.commit()
        assert client.get(reminders, headers=new).json()["total"] == (1 if status in {"revision_required", "pending_review"} else 0)
    assert client.put(url, headers=new, json={"subject": "数学", "teacher_id": seed_users["teacher2"], "reinforcement": "新老师填写"}).status_code == 200
    assert client.get(reminders, headers=new).json()["total"] == 0
    # 再分配回原老师时，旧填写记录不能消除新的任务。
    assert client.put(url + "/assignment", headers=manager, json={"teacher_id": teacher.id}).status_code == 200
    assert client.get(reminders, headers=old).json()["total"] == 1


def test_assignment_reminder_pagination_and_roles(client, auth, db, seed_users):
    class_id, other_class_id = _setup_subject_scope(db, seed_users)
    _, case_id, _ = _create_cycle_and_cases(client, auth, class_id, other_class_id, seed_users)
    teacher = db.query(User).filter_by(username="subject1").one()
    db.add(ClassTeacher(class_id=class_id, teacher_id=teacher.id, role="subject_teacher", subject="英语"))
    db.commit()
    manager, assignee = auth("teacher1"), auth("subject1")
    for subject in ["数学", "英语"]:
        assert client.put(f"/api/student-cases/{case_id}/subject-plans/{subject}/assignment", headers=manager, json={"teacher_id": teacher.id}).status_code == 200
    url = "/api/student-cases/subject-plan-reminders"
    first = client.get(url, params={"limit": 1}, headers=assignee).json()
    second = client.get(url, params={"limit": 1, "offset": 1}, headers=assignee).json()
    assert first["total"] == second["total"] == 2
    assert first["items"][0]["subject"] == "英语"
    assert second["items"][0]["subject"] == "数学"
    assert client.get(url, headers=auth("parent1")).status_code == 403
    assert client.get(url, headers=auth("admin")).status_code == 403
    assert client.get(url).status_code == 401
    assert client.get(url, params={"limit": 0}, headers=assignee).status_code == 422


def test_subject_teacher_register_with_invite(client, auth, db, seed_users):
    r = client.post(
        "/api/admin/invite-codes",
        headers=auth("admin"),
        json={"role": "subject_teacher"},
    )
    assert r.status_code == 200, r.text
    code = r.json()["code"]
    cap = client.get("/api/auth/captcha")
    assert cap.status_code == 200, cap.text
    captcha_id = cap.json()["captcha_id"]
    from app.services import captcha_service

    captcha_code, _exp = captcha_service._store[captcha_id]
    r = client.post(
        "/api/auth/register",
        json={
            "username": "13900000088",
            "password": "test123456",
            "name": "新任课老师",
            "role": "subject_teacher",
            "subject": "数学",
            "invite_code": code,
            "captcha_id": captcha_id,
            "captcha_code": captcha_code,
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "subject_teacher"
    assert db.query(User).filter_by(username="13900000088").one().subject == "数学"


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
