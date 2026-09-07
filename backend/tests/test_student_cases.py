"""一生一案核心验收：高三范围、权限隔离、状态机和版本不可覆盖。"""

from datetime import date, timedelta

from app.models.class_ import Class, ClassStudent, ClassTeacher
from app.models.student_case import (
    CaseAuditLog,
    CaseReview,
    CaseStudentProfile,
    CaseTask,
    CaseVersion,
    TaskCheckin,
)


def _setup_high3(db, seed_users):
    cls = Class(
        name="高三(1)班",
        grade="高三",
        school_year_starts_on=date(2025, 9, 1),
        teacher_id=seed_users["teacher1"],
    )
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


def _submit_and_approve(client, auth, case_id):
    submitted = client.post(
        f"/api/student-cases/{case_id}/transition",
        headers=auth("teacher1"),
        json={"target_status": "pending_confirmation", "reason": "提交德育审查"},
    )
    assert submitted.status_code == 200, submitted.text
    approved = client.post(
        f"/api/student-cases/{case_id}/deyu-review",
        headers=auth("deyu1"),
        json={"decision": "approved", "corrective_action": "审查通过"},
    )
    assert approved.status_code == 200, approved.text
    return approved


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


def test_create_case_stores_family_feedback_in_student_profile(client, auth, db, seed_users):
    class_id = _setup_high3(db, seed_users)
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
    created = client.post(
        "/api/student-cases",
        headers=auth("teacher1"),
        json={
            "cycle_id": cycle.json()["id"],
            "student_id": seed_users["student1"],
            "class_id": class_id,
            "owner_teacher_id": seed_users["teacher1"],
            "parent_evaluation": "学习态度认真，需加强时间管理。",
            "primary_needs": "希望获得数学基础巩固支持。",
            "current_summary": "班主任手工建档",
        },
    )
    assert created.status_code == 200, created.text
    assert created.json()["overall_problem"] == ""
    assert created.json()["admission_target"] == ""

    detail = client.get(f"/api/student-cases/{created.json()['id']}", headers=auth("teacher1"))
    assert detail.status_code == 200, detail.text
    assert detail.json()["class_starts_on"] == "2025-09-01"
    assert detail.json()["student_profile"]["parent_evaluation"].startswith("学习态度认真")
    assert detail.json()["student_profile"]["primary_needs"].startswith("希望获得数学")


def test_head_teacher_can_complete_student_profile_during_execution(
    client, auth, db, seed_users
):
    class_id = _setup_high3(db, seed_users)
    _, case_id = _create_cycle_and_case(client, auth, class_id, seed_users)

    initial = client.get(f"/api/student-cases/{case_id}", headers=auth("teacher1"))
    assert initial.status_code == 200, initial.text
    assert initial.json()["student_profile"]["student_name"] == "张三"
    assert initial.json()["student_profile"]["grade"] == "高三"

    _submit_and_approve(client, auth, case_id)

    payload = {
        "student_name": "张三",
        "gender": "男",
        "ethnicity": "汉族",
        "source_school": "西安市示范中学",
        "grade": "高三",
        "parent_evaluation": "学习态度认真，希望增强时间管理。",
        "primary_needs": "需要数学基础巩固与考前情绪支持。",
        "allergy_history": "花粉过敏",
        "underlying_conditions": "无",
        "other_health_notes": "体育活动前注意热身。",
    }
    saved = client.put(
        f"/api/student-cases/{case_id}/student-profile",
        headers=auth("teacher1"),
        json=payload,
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["source_school"] == "西安市示范中学"
    assert saved.json()["allergy_history"] == "花粉过敏"

    forbidden = client.put(
        f"/api/student-cases/{case_id}/student-profile",
        headers=auth("teacher2"),
        json=payload,
    )
    assert forbidden.status_code == 403

    detail = client.get(f"/api/student-cases/{case_id}", headers=auth("teacher1"))
    assert detail.status_code == 200, detail.text
    assert detail.json()["student_profile"]["primary_needs"].startswith("需要数学")
    assert db.query(CaseStudentProfile).filter_by(student_case_id=case_id).count() == 1
    assert db.query(CaseAuditLog).filter_by(
        student_case_id=case_id,
        action="student_profile.upsert",
    ).count() == 1


def test_profile_save_preserves_omitted_guardian_information(client, auth, db, seed_users):
    from app.models.class_ import StudentGuardian
    from app.models.user import User

    class_id = _setup_high3(db, seed_users)
    _, case_id = _create_cycle_and_case(client, auth, class_id, seed_users)
    profile = db.query(CaseStudentProfile).filter_by(student_case_id=case_id).one()
    # 历史联系方式即使不是手机号，也不能因隐藏字段而阻止学生资料保存。
    profile.parent_name = "已有家长"
    profile.parent_phone = "历史固定电话"
    profile.parent_relationship = "母亲"
    db.add(StudentGuardian(parent_id=seed_users["parent1"], student_id=seed_users["student1"]))
    db.commit()
    user_count = db.query(User).count()
    response = client.put(f"/api/student-cases/{case_id}/student-profile", headers=auth("teacher1"),
                          json={"student_name": "张三", "source_school": "新学校", "parent_evaluation": "继续保持"})
    assert response.status_code == 200, response.text
    assert response.json()["source_school"] == "新学校"
    assert response.json()["parent_evaluation"] == "继续保持"
    assert response.json()["parent_name"] == "已有家长"
    assert response.json()["parent_phone"] == "历史固定电话"
    assert response.json()["parent_relationship"] == "母亲"
    assert db.query(User).count() == user_count
    assert db.query(StudentGuardian).filter_by(parent_id=seed_users["parent1"], student_id=seed_users["student1"]).count() == 1


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

    submitted = client.post(
        f"/api/student-cases/{case_id}/transition",
        headers=auth("teacher1"),
        json={"target_status": "pending_confirmation", "reason": "提交审查"},
    )
    assert submitted.status_code == 200, submitted.text
    self_approved = client.post(
        f"/api/student-cases/{case_id}/transition",
        headers=auth("teacher1"),
        json={"target_status": "executing", "reason": "越权自审"},
    )
    assert self_approved.status_code == 403
    _submit_and_approve_after_submission = client.post(
        f"/api/student-cases/{case_id}/deyu-review",
        headers=auth("deyu1"),
        json={"decision": "approved", "corrective_action": "审查通过"},
    )
    assert _submit_and_approve_after_submission.status_code == 200, _submit_and_approve_after_submission.text

    for target in ("pending_review", "adjusted"):
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


def test_deyu_can_return_to_head_teacher_and_close_after_resubmission(client, auth, db, seed_users):
    class_id = _setup_high3(db, seed_users)
    _, case_id = _create_cycle_and_case(client, auth, class_id, seed_users)
    linked = client.post(
        "/api/admin/guardian-links",
        headers=auth("admin"),
        json={"parent_id": seed_users["parent1"], "student_id": seed_users["student1"], "relationship": "father"},
    )
    assert linked.status_code == 200, linked.text
    submitted = client.post(
        f"/api/student-cases/{case_id}/transition",
        headers=auth("teacher1"),
        json={"target_status": "pending_confirmation", "reason": "提交德育审查"},
    )
    assert submitted.status_code == 200, submitted.text

    incomplete = client.post(
        f"/api/student-cases/{case_id}/deyu-review",
        headers=auth("deyu1"),
        json={"decision": "changes_requested", "problem": "目标不具体"},
    )
    assert incomplete.status_code == 400

    returned = client.post(
        f"/api/student-cases/{case_id}/deyu-review",
        headers=auth("deyu1"),
        json={
            "decision": "changes_requested",
            "subject": "数学",
            "problem": "数学目标缺少量化标准",
            "corrective_action": "补充阶段目标分数和周任务",
            "correction_due_on": str(date.today() + timedelta(days=3)),
        },
    )
    assert returned.status_code == 200, returned.text
    assert returned.json()["workflow_status"] == "open"
    assert returned.json()["assigned_to"] == seed_users["teacher1"]

    teacher_detail = client.get(f"/api/student-cases/{case_id}", headers=auth("teacher1"))
    assert teacher_detail.status_code == 200
    assert teacher_detail.json()["status"] == "revision_required"
    assert teacher_detail.json()["reviews"][0]["corrective_action"].startswith("补充阶段")

    revised = client.patch(
        f"/api/student-cases/{case_id}",
        headers=auth("teacher1"),
        json={"current_summary": "已补充数学阶段目标和周任务"},
    )
    assert revised.status_code == 200, revised.text
    resubmitted = client.post(
        f"/api/student-cases/{case_id}/transition",
        headers=auth("teacher1"),
        json={"target_status": "pending_confirmation", "reason": "已按意见完成整改"},
    )
    assert resubmitted.status_code == 200, resubmitted.text
    review = db.query(CaseReview).filter_by(student_case_id=case_id, decision="changes_requested").one()
    assert review.workflow_status == "resubmitted"
    assert review.resubmitted_at is not None

    approved = client.post(
        f"/api/student-cases/{case_id}/deyu-review",
        headers=auth("deyu1"),
        json={"decision": "approved", "corrective_action": "整改符合要求"},
    )
    assert approved.status_code == 200, approved.text
    assert client.get(f"/api/student-cases/{case_id}", headers=auth("teacher1")).json()["status"] == "executing"
    parent_detail = client.get(f"/api/student-cases/{case_id}", headers=auth("parent1"))
    assert parent_detail.status_code == 200, parent_detail.text
    assert parent_detail.json()["reviews"] == []
    db.refresh(review)
    assert review.workflow_status == "closed"
    assert review.resolved_at is not None


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


def test_stage_review_requires_deyu_approval_before_publish(client, auth, db, seed_users):
    """阶段复盘链路：复盘态可编辑下一阶段内容，已调整须送审，德育通过后才能发布。"""
    class_id = _setup_high3(db, seed_users)
    _, case_id = _create_cycle_and_case(client, auth, class_id, seed_users)
    _submit_and_approve(client, auth, case_id)
    assert client.get(f"/api/student-cases/{case_id}", headers=auth("teacher1")).json()["status"] == "executing"

    # 1. 发起阶段复盘
    review = client.post(
        f"/api/student-cases/{case_id}/transition",
        headers=auth("teacher1"),
        json={"target_status": "pending_review", "reason": "发起阶段复盘"},
    )
    assert review.status_code == 200, review.text

    # 2. 复盘态可编辑下一阶段内容：总案、学科方案、任务
    edit_overview = client.patch(
        f"/api/student-cases/{case_id}",
        headers=auth("teacher1"),
        json={"overall_problem": "复盘：数学压轴薄弱，下阶段主攻导数"},
    )
    assert edit_overview.status_code == 200, edit_overview.text
    edit_plan = client.put(
        f"/api/student-cases/{case_id}/subject-plans/数学",
        headers=auth("teacher1"),
        json={
            "subject": "数学",
            "teacher_id": seed_users["teacher1"],
            "problem_location": "导数综合薄弱",
            "struggle_goal": "稳定110+",
        },
    )
    assert edit_plan.status_code == 200, edit_plan.text
    new_task = client.post(
        f"/api/student-cases/{case_id}/tasks",
        headers=auth("teacher1"),
        json={
            "subject": "数学",
            "title": "导数每日一练",
            "cadence": "daily",
            "starts_on": str(date.today()),
            "due_on": str(date.today() + timedelta(days=14)),
        },
    )
    assert new_task.status_code == 200, new_task.text

    # 3. 确认调整生成新版本
    adjusted = client.post(
        f"/api/student-cases/{case_id}/transition",
        headers=auth("teacher1"),
        json={"target_status": "adjusted", "reason": "阶段复盘已调整"},
    )
    assert adjusted.status_code == 200, adjusted.text
    assert adjusted.json()["version"] == 2

    # 4. 已调整不可直发执行，必须先送审
    direct_publish = client.post(
        f"/api/student-cases/{case_id}/transition",
        headers=auth("teacher1"),
        json={"target_status": "executing", "reason": "直接发布"},
    )
    assert direct_publish.status_code == 403

    # 5. 已调整（待送审）锁定内容编辑
    assert client.patch(
        f"/api/student-cases/{case_id}",
        headers=auth("teacher1"),
        json={"overall_problem": "送审后偷改"},
    ).status_code == 409
    assert client.put(
        f"/api/student-cases/{case_id}/subject-plans/数学",
        headers=auth("teacher1"),
        json={"subject": "数学", "teacher_id": seed_users["teacher1"]},
    ).status_code == 409
    assert client.post(
        f"/api/student-cases/{case_id}/tasks",
        headers=auth("teacher1"),
        json={
            "subject": "数学",
            "title": "送审后加任务",
            "cadence": "daily",
            "starts_on": str(date.today()),
            "due_on": str(date.today() + timedelta(days=7)),
        },
    ).status_code == 409

    # 6. 提交德育审核，状态进入待确认，德育待办可见
    submitted = client.post(
        f"/api/student-cases/{case_id}/transition",
        headers=auth("teacher1"),
        json={"target_status": "pending_confirmation", "reason": "复盘调整完成，提交德育审核"},
    )
    assert submitted.status_code == 200, submitted.text
    pending = client.get("/api/student-cases", params={"status": "pending_confirmation"}, headers=auth("deyu1"))
    assert pending.status_code == 200, pending.text
    assert case_id in [item["id"] for item in pending.json()]

    # 7. 德育打回：字段不全 400，补全后退回班主任继续复盘
    incomplete = client.post(
        f"/api/student-cases/{case_id}/deyu-review",
        headers=auth("deyu1"),
        json={"decision": "changes_requested", "problem": "目标不够具体"},
    )
    assert incomplete.status_code == 400
    returned = client.post(
        f"/api/student-cases/{case_id}/deyu-review",
        headers=auth("deyu1"),
        json={
            "decision": "changes_requested",
            "subject": "数学",
            "problem": "下阶段目标不够具体",
            "corrective_action": "补充导数模块量化目标",
            "correction_due_on": str(date.today() + timedelta(days=3)),
        },
    )
    assert returned.status_code == 200, returned.text
    assert returned.json()["workflow_status"] == "open"
    assert client.get(f"/api/student-cases/{case_id}", headers=auth("teacher1")).json()["status"] == "revision_required"

    # 8. 整改后重新送审，复盘退回意见自动标记为已重新提交
    resubmitted = client.post(
        f"/api/student-cases/{case_id}/transition",
        headers=auth("teacher1"),
        json={"target_status": "pending_confirmation", "reason": "已补充量化目标"},
    )
    assert resubmitted.status_code == 200, resubmitted.text
    review_row = db.query(CaseReview).filter_by(student_case_id=case_id, decision="changes_requested").order_by(CaseReview.id.desc()).first()
    assert review_row.workflow_status == "resubmitted"

    # 9. 德育通过后自动发布进入执行，家长可见新版本
    linked = client.post(
        "/api/admin/guardian-links",
        headers=auth("admin"),
        json={"parent_id": seed_users["parent1"], "student_id": seed_users["student1"], "relationship": "father"},
    )
    assert linked.status_code == 200, linked.text
    approved = client.post(
        f"/api/student-cases/{case_id}/deyu-review",
        headers=auth("deyu1"),
        json={"decision": "approved", "corrective_action": "复盘调整同意发布"},
    )
    assert approved.status_code == 200, approved.text
    detail = client.get(f"/api/student-cases/{case_id}", headers=auth("teacher1"))
    assert detail.json()["status"] == "executing"
    assert detail.json()["version"] == 2
    parent_detail = client.get(f"/api/student-cases/{case_id}", headers=auth("parent1"))
    assert parent_detail.status_code == 200, parent_detail.text
    assert parent_detail.json()["version"] == 2
