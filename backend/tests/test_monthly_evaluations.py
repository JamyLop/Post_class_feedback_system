"""任课老师月度评定：查看所带班级评定、独立提交学科评价，互不覆盖。"""

from app.core.security import hash_password
from app.models.class_ import Class, ClassStudent, ClassTeacher, StudentGuardian
from app.models.monthly_report import MonthlyReportEvaluation
from app.models.user import ROLE_SUBJECT_TEACHER, User


def _setup(db, seed_users):
    subject = User(username="subject1", name="数学老师", role=ROLE_SUBJECT_TEACHER,
                   password_hash=hash_password("test123456"), subject="数学")
    db.add(subject)
    db.flush()
    cls = Class(name="月评任课班", grade="高三", teacher_id=seed_users["teacher1"])
    other = Class(name="月评无关班", grade="高三", teacher_id=seed_users["teacher2"])
    db.add_all([cls, other])
    db.flush()
    db.add_all([
        ClassStudent(class_id=cls.id, student_id=seed_users["student1"]),
        ClassStudent(class_id=other.id, student_id=seed_users["student2"]),
        ClassTeacher(class_id=cls.id, teacher_id=subject.id, role="subject_teacher", subject="数学"),
        StudentGuardian(parent_id=seed_users["parent1"], student_id=seed_users["student1"]),
    ])
    db.commit()
    return subject, cls, other


def _create_report(client, auth, cls, student_id, teacher="teacher1"):
    r = client.post("/api/monthly-reports", headers=auth(teacher), json={
        "student_id": student_id, "class_id": cls.id,
        "month_label": "2026-09", "final_content": "本月表现良好，下月加强复盘。",
    })
    assert r.status_code == 200, r.text
    return r.json()


def test_subject_teacher_reads_own_class_and_evaluates_independently(client, auth, db, seed_users):
    _setup(db, seed_users)
    report = _create_report(client, auth, db.get(Class, db.query(Class).filter_by(name="月评任课班").one().id), seed_users["student1"])

    # 任课老师列表仅见所带班级
    rows = client.get("/api/monthly-reports", headers=auth("subject1")).json()
    assert [r["id"] for r in rows] == [report["id"]]
    assert rows[0]["can_evaluate"] is True

    # 学科评价 + 班主任评价互不覆盖
    url = f"/api/monthly-reports/{report['id']}/evaluation"
    s = client.put(url, headers=auth("subject1"), json={"content": "  数学函数需加强  "})
    assert s.status_code == 200, s.text
    assert s.json()["evaluations"][0]["teacher_role"] == "subject_teacher"
    assert s.json()["evaluations"][0]["subject"] == "数学"
    assert s.json()["evaluations"][0]["content"] == "数学函数需加强"

    h = client.put(url, headers=auth("teacher1"), json={"content": "整体有进步"})
    assert h.status_code == 200, h.text
    assert len(h.json()["evaluations"]) == 2

    # 任课老师修改自己的评价不影响班主任
    original = next(e for e in h.json()["evaluations"] if e["teacher_role"] == "subject_teacher")
    u = client.put(url, headers=auth("subject1"), json={"content": "数学函数与几何需加强"})
    assert u.status_code == 200, u.text
    data = u.json()
    assert len(data["evaluations"]) == 2
    head = next(e for e in data["evaluations"] if e["teacher_role"] == "head_teacher")
    subj = next(e for e in data["evaluations"] if e["teacher_role"] == "subject_teacher")
    assert head["content"] == "整体有进步"
    assert subj["id"] == original["id"] and subj["created_at"] == original["created_at"]
    assert data["final_content"] == "整体有进步"

    # 发布后学生/家长可见定稿 + 全部学科评价
    assert client.post(f"/api/monthly-reports/{report['id']}/publish", headers=auth("teacher1")).status_code == 200
    for viewer in ("student1", "parent1"):
        got = client.get(f"/api/monthly-reports/{report['id']}", headers=auth(viewer))
        assert got.status_code == 200, got.text
        assert len(got.json()["evaluations"]) == 2
        assert got.json()["can_evaluate"] is False


def test_subject_teacher_scope_and_validation(client, auth, db, seed_users):
    _, cls, other = _setup(db, seed_users)
    report = _create_report(client, auth, cls, seed_users["student1"])
    other_report = _create_report(client, auth, other, seed_users["student2"], teacher="teacher2")
    url = f"/api/monthly-reports/{report['id']}/evaluation"

    # 无关班级不可见、不可评价
    assert client.get(f"/api/monthly-reports/{other_report['id']}", headers=auth("subject1")).status_code == 403
    assert client.put(f"/api/monthly-reports/{other_report['id']}/evaluation",
                      headers=auth("subject1"), json={"content": "越界"}).status_code == 403
    # 无评价权限角色拒绝
    for user in ("admin", "student1", "parent1", "deyu1", "teacher2"):
        r = client.put(url, headers=auth(user), json={"content": "无权评价"})
        assert r.status_code == 403, (user, r.text)
    # 非法内容与冒名字段拒绝
    for payload in ({"content": " \n "}, {"content": "字" * 2001},
                    {"content": "冒名", "teacher_id": 1}, {"content": "冒名", "teacher_role": "head_teacher"}):
        r = client.put(url, headers=auth("subject1"), json=payload)
        assert r.status_code == 422, r.text
    assert client.put("/api/monthly-reports/999999/evaluation",
                      headers=auth("subject1"), json={"content": "评价"}).status_code == 404
    # 任课老师能独立新建学科评定，但不能修改/发布/删除德育定稿
    assert client.post("/api/monthly-reports", headers=auth("subject1"), json={
        "student_id": seed_users["student1"], "class_id": cls.id,
        "month_label": "2026-10", "final_content": "本人学科"}).status_code == 200
    assert client.put(f"/api/monthly-reports/{report['id']}",
                      headers=auth("subject1"), json={"final_content": "越权修改"}).status_code == 403
    assert client.post(f"/api/monthly-reports/{report['id']}/publish",
                       headers=auth("subject1")).status_code == 403
    assert client.delete(f"/api/monthly-reports/{report['id']}",
                         headers=auth("subject1")).status_code == 403


def test_monthly_delete_cascades_evaluations(client, auth, db, seed_users):
    _, cls, _ = _setup(db, seed_users)
    report = _create_report(client, auth, cls, seed_users["student1"])
    url = f"/api/monthly-reports/{report['id']}/evaluation"
    assert client.put(url, headers=auth("subject1"), json={"content": "学科评价"}).status_code == 200
    assert client.delete(f"/api/monthly-reports/{report['id']}", headers=auth("teacher1")).status_code == 200
    assert db.query(MonthlyReportEvaluation).filter_by(report_id=report["id"]).count() == 0


def test_three_part_review_and_head_only_management(client, auth, db, seed_users):
    _, cls, _ = _setup(db, seed_users)
    report = _create_report(client, auth, cls, seed_users["student1"])
    url = f"/api/monthly-reports/{report['id']}"
    review = "【总结】\n本月进步\n\n【问题】\n复盘不足\n\n【计划】\n每周复盘"
    result = client.put(url + "/evaluation", headers=auth("subject1"), json={"content": review})
    assert result.status_code == 200, result.text
    assert result.json()["evaluations"][0]["content"] == review
    assert result.json()["evaluation_subject"] == "数学"
    assert result.json()["can_manage"] is False
    incomplete = review.replace("复盘不足", " ")
    assert client.put(url + "/evaluation", headers=auth("subject1"), json={"content": incomplete}).status_code == 422
    assert client.put(url, headers=auth("teacher1"), json={"final_content": incomplete}).status_code == 422
    # teacher 账号有任课关系也不能代写德育或发布、删除。
    db.add(ClassTeacher(class_id=cls.id, teacher_id=seed_users["teacher2"], role="subject_teacher", subject="英语"))
    db.commit()
    assert client.put(url, headers=auth("teacher2"), json={"final_content": review}).status_code == 403
    assert client.post(url + "/publish", headers=auth("teacher2")).status_code == 403
    assert client.delete(url, headers=auth("teacher2")).status_code == 403
    assert client.put(url, headers=auth("admin"), json={"final_content": review}).status_code == 403
    assert client.put(url, headers=auth("teacher1"), json={"final_content": review}).status_code == 200
    assert client.get(url, headers=auth("teacher1")).json()["can_manage"] is True


def test_student_assignment_overrides_class_subject_teacher(client, auth, db, seed_users):
    from datetime import date
    from app.models.student_case import CaseCycle, StudentCase, SubjectPlan
    _, cls, _ = _setup(db, seed_users)
    cycle = CaseCycle(name="测试周期", grade="高三", school_year="2026", starts_on=date(2026, 9, 1), ends_on=date(2027, 7, 1))
    db.add(cycle)
    db.flush()
    case = StudentCase(cycle_id=cycle.id, student_id=seed_users["student1"], class_id=cls.id, owner_teacher_id=seed_users["teacher1"])
    db.add(case)
    db.flush()
    # 该生数学指定另一名老师，即使原老师仍有班级数学关系也不能代填。
    db.add(SubjectPlan(student_case_id=case.id, subject="数学", teacher_id=seed_users["teacher2"]))
    db.commit()
    report = _create_report(client, auth, cls, seed_users["student1"])
    url = f"/api/monthly-reports/{report['id']}"
    assert client.get(url, headers=auth("subject1")).json()["can_evaluate"] is False
    assert client.put(url + "/evaluation", headers=auth("subject1"), json={"content": "代填"}).status_code == 403
    assigned = client.get(url, headers=auth("teacher2"))
    assert assigned.status_code == 200
    assert assigned.json()["evaluation_subject"] == "数学"
    assert assigned.json()["can_manage"] is False
    assert any(row["id"] == report["id"] for row in client.get("/api/monthly-reports", headers=auth("teacher2")).json())
    assert client.put(url + "/evaluation", headers=auth("teacher2"), json={"content": "本人评价"}).status_code == 200


def test_subject_can_start_report_before_head_teacher(client, auth, db, seed_users):
    _, cls, _ = _setup(db, seed_users)
    payload = {"student_id": seed_users["student1"], "class_id": cls.id, "month_label": "2026-10", "final_content": "【总结】\n进步\n\n【问题】\n计算\n\n【计划】\n练习"}
    first = client.post("/api/monthly-reports", headers=auth("subject1"), json=payload)
    assert first.status_code == 200, first.text
    row = first.json()
    assert row["final_content"] == ""
    assert row["evaluations"][0]["content"] == payload["final_content"]
    url = f"/api/monthly-reports/{row['id']}"
    assert client.post(url + "/publish", headers=auth("teacher1")).status_code == 409
    head = client.post("/api/monthly-reports", headers=auth("teacher1"), json={**payload, "final_content": "德育总结"})
    assert head.status_code == 200, head.text
    assert head.json()["id"] == row["id"]
    assert head.json()["evaluations"] == row["evaluations"]
    assert client.post(url + "/publish", headers=auth("teacher1")).status_code == 200


def test_head_teacher_teaching_subject_keeps_deyu_separate(client, auth, db, seed_users):
    _, cls, _ = _setup(db, seed_users)
    db.add(ClassTeacher(class_id=cls.id, teacher_id=seed_users["teacher1"], role="subject_teacher", subject="英语"))
    db.commit()
    report = _create_report(client, auth, cls, seed_users["student1"])
    assert report["can_manage"] is True
    assert report["evaluation_subject"] == "英语"
    result = client.put(f"/api/monthly-reports/{report['id']}/evaluation", headers=auth("teacher1"), json={"content": "英语总结"})
    assert result.status_code == 200
    assert result.json()["final_content"] == report["final_content"]
    assert result.json()["evaluations"][0]["teacher_role"] == "subject_teacher"
