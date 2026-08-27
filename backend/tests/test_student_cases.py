"""一生一案核心验收：高三范围、权限隔离、状态机和版本不可覆盖。"""

from datetime import date, timedelta

from app.models.class_ import Class, ClassStudent, ClassTeacher
from app.models.student_case import CaseAuditLog, CaseTask, CaseVersion, TaskCheckin


def _setup_high3(db, seed_users):
    cls = Class(name="高三(1)班", grade="高三", teacher_id=seed_users["teacher1"])
    db.add(cls)
    db.flush()
    db.add_all([
        ClassStudent(class_id=cls.id, student_id=seed_users["student1"]),
        ClassStudent(class_id=cls.id, student_id=seed_users["student2"]),
        ClassTeacher(
            class_id=cls.id,
            teacher_id=seed_users["teacher2"],
            role="subject_teacher",
            subject="数学",
        ),
    ])
    db.commit()
    return cls.id


def _create_cycle_and_case(client, auth, class_id, seed_users):
    cycle = client.post(
        "/api/student-cases/cycles",
        headers=auth("admin"),
        json={
            "name": "2026届高三备考周期",
            "school_year": "2025-2026",
            "starts_on": str(date.today()),
            "ends_on": str(date.today() + timedelta(days=180)),
        },
    )
    assert cycle.status_code == 200, cycle.text
    case = client.post(
        "/api/student-cases",
        headers=auth("teacher1"),
        json={
            "cycle_id": cycle.json()["id"],
            "student_id": seed_users["student1"],
            "class_id": class_id,
            "owner_teacher_id": seed_users["teacher1"],
            "overall_problem": "数学基础不牢",
            "admission_target": "一本院校",
            "current_summary": "进入第一轮复习",
        },
    )
    assert case.status_code == 200, case.text
    return cycle.json()["id"], case.json()["id"]


def test_high3_only_and_unique_case(client, auth, db, seed_users):
    class_id = _setup_high3(db, seed_users)
    cycle_id, case_id = _create_cycle_and_case(client, auth, class_id, seed_users)

    duplicate = client.post(
        "/api/student-cases",
        headers=auth("teacher1"),
        json={
            "cycle_id": cycle_id,
            "student_id": seed_users["student1"],
            "class_id": class_id,
            "owner_teacher_id": seed_users["teacher1"],
        },
    )
    assert duplicate.status_code == 409
    assert case_id > 0


def test_status_permission_and_immutable_version(client, auth, db, seed_users):
    class_id = _setup_high3(db, seed_users)
    _, case_id = _create_cycle_and_case(client, auth, class_id, seed_users)

    # 一生一案不由学生维护；学生继续使用原作业系统，但不能访问家长档案。
    hidden = client.get(f"/api/student-cases/{case_id}", headers=auth("student1"))
    assert hidden.status_code == 403
    assert client.get("/api/student-cases", headers=auth("student1")).json() == []

    linked = client.post(
        "/api/admin/guardian-links",
        headers=auth("admin"),
        json={
            "parent_id": seed_users["parent1"],
            "student_id": seed_users["student1"],
            "relationship": "father",
        },
    )
    assert linked.status_code == 200, linked.text
    assert linked.json()["parent_name"] == "张三家长"
    parent_hidden = client.get(f"/api/student-cases/{case_id}", headers=auth("parent1"))
    assert parent_hidden.status_code == 403

    for target in ("pending_confirmation", "executing", "pending_review", "adjusted"):
        changed = client.post(
            f"/api/student-cases/{case_id}/transition",
            headers=auth("teacher1"),
            json={"target_status": target, "reason": "阶段验收"},
        )
        assert changed.status_code == 200, changed.text

    visible = client.get(f"/api/student-cases/{case_id}", headers=auth("parent1"))
    assert visible.status_code == 200
    assert visible.json()["version"] == 2
    children = client.get("/api/student-cases/children", headers=auth("parent1"))
    assert [item["id"] for item in children.json()] == [case_id]

    versions = client.get(
        f"/api/student-cases/{case_id}/versions", headers=auth("teacher1")
    )
    assert versions.status_code == 200
    assert versions.json()[0]["version"] == 1
    assert versions.json()[0]["snapshot"]["case"]["status"] == "pending_review"
    assert db.query(CaseVersion).filter_by(student_case_id=case_id).count() == 1
    assert db.query(CaseAuditLog).filter_by(student_case_id=case_id).count() >= 5

    # 执行期字段更新被拒绝，不能绕过版本机制无痕覆盖。
    blocked = client.patch(
        f"/api/student-cases/{case_id}",
        headers=auth("teacher1"),
        json={"overall_problem": "直接覆盖"},
    )
    assert blocked.status_code == 409


def test_only_head_teacher_can_manage_case_content(client, auth, db, seed_users):
    class_id = _setup_high3(db, seed_users)
    _, case_id = _create_cycle_and_case(client, auth, class_id, seed_users)

    math = client.put(
        f"/api/student-cases/{case_id}/subject-plans/数学",
        headers=auth("teacher2"),
        json={
            "subject": "数学",
            "teacher_id": seed_users["teacher2"],
            "problem_location": "函数模块薄弱",
            "cause_analysis": "基础题失分",
            "struggle_goal": "稳定到110分",
            "gaokao_requirement": "先保基础分",
            "reinforcement": "每日限时训练",
        },
    )
    assert math.status_code == 403

    chinese = client.put(
        f"/api/student-cases/{case_id}/subject-plans/语文",
        headers=auth("teacher2"),
        json={"subject": "语文", "teacher_id": seed_users["teacher2"]},
    )
    assert chinese.status_code == 403

    admin_update = client.patch(
        f"/api/student-cases/{case_id}",
        headers=auth("admin"),
        json={"overall_problem": "管理员直接改写"},
    )
    assert admin_update.status_code == 403

    school_review = client.post(
        f"/api/student-cases/{case_id}/reviews",
        headers=auth("teacher1"),
        json={"review_level": "school", "problem": "测试越权"},
    )
    assert school_review.status_code == 403


def test_case_detail_includes_task_checkins(client, auth, db, seed_users):
    class_id = _setup_high3(db, seed_users)
    _, case_id = _create_cycle_and_case(client, auth, class_id, seed_users)
    task = CaseTask(
        student_case_id=case_id,
        subject="数学",
        title="函数基础每日训练",
        cadence="daily",
        starts_on=date.today(),
        due_on=date.today() + timedelta(days=7),
        created_by=seed_users["teacher1"],
    )
    db.add(task)
    db.flush()
    db.add(TaskCheckin(
        task_id=task.id,
        student_id=seed_users["student1"],
        completion_rate=80,
        self_check="错题已完成二次订正",
    ))
    db.commit()

    updated = client.put(
        f"/api/student-cases/{case_id}/tasks/{task.id}",
        headers=auth("teacher1"),
        json={
            "subject": "数学",
            "title": "函数基础与错题复盘",
            "description": "完整保留教师填写的训练要求",
            "cadence": "weekly",
            "starts_on": str(date.today()),
            "due_on": str(date.today() + timedelta(days=14)),
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["title"] == "函数基础与错题复盘"

    checkin = client.post(
        f"/api/student-cases/tasks/{task.id}/checkins",
        headers=auth("teacher1"),
        json={"completion_rate": 90, "self_check": "班主任核实：本周训练按要求完成"},
    )
    assert checkin.status_code == 200, checkin.text
    assert checkin.json()["student_id"] == seed_users["student1"]

    student_checkin = client.post(
        f"/api/student-cases/tasks/{task.id}/checkins",
        headers=auth("student1"),
        json={"completion_rate": 100, "self_check": "学生自行录入"},
    )
    assert student_checkin.status_code == 403

    response = client.get(f"/api/student-cases/{case_id}", headers=auth("teacher1"))
    assert response.status_code == 200, response.text
    assert response.json()["task_checkins"][0]["task_id"] == task.id
    assert response.json()["task_checkins"][0]["completion_rate"] == 90
