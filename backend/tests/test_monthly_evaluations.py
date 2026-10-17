"""任课老师月度评定：查看所带班级评定、独立提交学科评价，互不覆盖。"""

import pytest

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
    from datetime import date
    from app.models.student_case import CaseCycle, StudentCase, SubjectPlan
    cycle = CaseCycle(name="月评初评范围", grade="高三", school_year="2026", starts_on=date(2026, 9, 1), ends_on=date(2027, 7, 1))
    db.add(cycle)
    db.flush()
    for sid, classroom, owner in ((seed_users["student1"], cls, seed_users["teacher1"]), (seed_users["student3"], cls, seed_users["teacher1"]), (seed_users["student2"], other, seed_users["teacher2"])):
        case = StudentCase(cycle_id=cycle.id, student_id=sid, class_id=classroom.id, owner_teacher_id=owner)
        db.add(case)
        db.flush()
        for course in ("数学", "德育"):
            db.add(SubjectPlan(student_case_id=case.id, subject=course, teacher_id=owner))
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


@pytest.mark.parametrize("legacy_name", ["", "误填姓名"])
def test_head_placeholder_does_not_block_class_subject_teacher(client, auth, db, seed_users, legacy_name):
    from datetime import date
    from app.models.student_case import CaseCycle, StudentCase, SubjectPlan

    _, cls, _ = _setup(db, seed_users)
    cycle = CaseCycle(name="旧档案周期", grade="高三", school_year="2026",
                      starts_on=date(2026, 9, 1), ends_on=date(2027, 7, 1))
    db.add(cycle)
    db.flush()
    case = StudentCase(cycle_id=cycle.id, student_id=seed_users["student1"],
                       class_id=cls.id, owner_teacher_id=seed_users["teacher1"])
    db.add(case)
    db.flush()
    db.add(SubjectPlan(student_case_id=case.id, subject="数学",
                       teacher_id=seed_users["teacher1"], teacher_name=legacy_name))
    db.commit()
    payload = {"student_id": seed_users["student1"], "class_id": cls.id,
               "student_case_id": case.id, "month_label": "2026-10", "final_content": "数学评价"}
    result = client.post("/api/monthly-reports", headers=auth("subject1"), json=payload)
    assert result.status_code == 200, result.text
    report = result.json()
    assert report["evaluation_subject"] == "数学"
    assert report["can_manage"] is False
    url = f"/api/monthly-reports/{report['id']}"
    assert client.put(url + "/evaluation", headers=auth("subject1"), json={"content": "修改数学评价"}).status_code == 200
    head = client.get(url, headers=auth("teacher1")).json()
    assert head["evaluation_subject"] == "" and head["can_manage"] is True
    assert client.put(url, headers=auth("subject1"), json={"final_content": "代写德育"}).status_code == 403
    assert client.put(url + "/evaluation", headers=auth("teacher2"), json={"content": "无关老师"}).status_code == 403


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
    from app.models.student_case import StudentCase, SubjectPlan
    for initial_case in db.query(StudentCase).filter_by(class_id=cls.id).all():
        db.add(SubjectPlan(student_case_id=initial_case.id, subject="英语", teacher_id=seed_users["teacher1"]))
    db.commit()
    report = _create_report(client, auth, cls, seed_users["student1"])
    assert report["can_manage"] is True
    assert report["evaluation_subject"] == "英语"
    result = client.put(f"/api/monthly-reports/{report['id']}/evaluation", headers=auth("teacher1"), json={"content": "英语总结"})
    assert result.status_code == 200
    assert result.json()["final_content"] == report["final_content"]
    assert result.json()["evaluations"][0]["teacher_role"] == "subject_teacher"


def test_writing_status_includes_uncreated_reports_and_filters_before_pagination(client, auth, db, seed_users):
    _, cls, _ = _setup(db, seed_users)
    db.add(ClassStudent(class_id=cls.id, student_id=seed_users["student3"]))
    db.commit()
    headers = auth("subject1")
    params = {"month_label": "2026-09", "limit": 1}
    response = client.get("/api/monthly-reports/writing-status", headers=headers, params=params)
    assert response.status_code == 200, response.text
    data = response.json()
    assert (data["total"], data["written"], data["unwritten"], data["filtered_total"]) == (2, 0, 2, 2)
    assert len(data["items"]) == 1
    assert data["items"][0]["report_id"] is None
    second = client.get("/api/monthly-reports/writing-status", headers=headers, params={**params, "offset": 1}).json()
    assert second["items"][0]["student_id"] != data["items"][0]["student_id"]
    assert seed_users["student2"] not in {data["items"][0]["student_id"], second["items"][0]["student_id"]}
    empty = client.get("/api/monthly-reports/writing-status", headers=headers, params={**params, "writing_status": "written"}).json()
    assert empty["items"] == [] and empty["total"] == 2 and empty["filtered_total"] == 0


def test_writing_status_counts_own_content_independently_of_publication(client, auth, db, seed_users):
    _, cls, _ = _setup(db, seed_users)
    report = _create_report(client, auth, cls, seed_users["student1"])
    url = "/api/monthly-reports/writing-status"
    params = {"month_label": "2026-09"}
    subject_headers = auth("subject1")
    head_headers = auth("teacher1")
    assert client.get(url, headers=subject_headers, params=params).json()["unwritten"] == 1
    assert client.get(url, headers=head_headers, params=params).json()["written"] == 1
    assert client.post(f"/api/monthly-reports/{report['id']}/publish", headers=head_headers).status_code == 200
    assert client.get(url, headers=subject_headers, params=params).json()["unwritten"] == 1
    assert client.put(f"/api/monthly-reports/{report['id']}/evaluation", headers=subject_headers, json={"content": "数学评定"}).status_code == 200
    data = client.get(url, headers=subject_headers, params={**params, "writing_status": "written"}).json()
    assert data["written"] == 1 and data["items"][0]["report_id"] == report["id"]
    assert client.get(url, headers=subject_headers, params={"month_label": "2026-10"}).json()["unwritten"] == 1
    assert client.get(url, headers=subject_headers, params={**params, "keyword": "不存在"}).json()["total"] == 0


def test_writing_status_dual_role_and_explicit_subject_creation(client, auth, db, seed_users):
    _, cls, _ = _setup(db, seed_users)
    db.add(ClassTeacher(class_id=cls.id, teacher_id=seed_users["teacher1"], role="subject_teacher", subject="英语"))
    from app.models.student_case import StudentCase, SubjectPlan
    for initial_case in db.query(StudentCase).filter_by(class_id=cls.id).all():
        db.add(SubjectPlan(student_case_id=initial_case.id, subject="英语", teacher_id=seed_users["teacher1"]))
    db.commit()
    headers = auth("teacher1")
    params = {"month_label": "2026-09"}
    before = client.get("/api/monthly-reports/writing-status", headers=headers, params=params).json()
    assert before["total"] == 3 and before["unwritten"] == 3
    response = client.post("/api/monthly-reports", headers=headers, json={
        "student_id": seed_users["student1"], "class_id": cls.id, "month_label": "2026-09",
        "final_content": "英语评价", "evaluation_role": "subject_teacher",
    })
    assert response.status_code == 200, response.text
    assert response.json()["final_content"] == ""
    assert response.json()["evaluations"][0]["subject"] == "英语"
    after = client.get("/api/monthly-reports/writing-status", headers=headers, params=params).json()
    states = {r["subject"]: r["writing_status"] for r in after["items"]}
    assert states == {"德育": "unwritten", "英语": "written", "数学": "unwritten"}
    assert after["written"] == 1 and after["unwritten"] == 2


def test_writing_status_respects_student_assignment_and_plan_only_teacher(client, auth, db, seed_users):
    from datetime import date
    from app.models.student_case import CaseCycle, StudentCase, SubjectPlan
    _, cls, _ = _setup(db, seed_users)
    cycle = CaseCycle(name="月评查询周期", grade="高三", school_year="2026", starts_on=date(2026, 9, 1), ends_on=date(2027, 6, 30))
    db.add(cycle)
    db.flush()
    case = StudentCase(cycle_id=cycle.id, student_id=seed_users["student1"], class_id=cls.id, owner_teacher_id=seed_users["teacher1"])
    db.add(case)
    db.flush()
    db.add(SubjectPlan(student_case_id=case.id, subject="数学", teacher_id=seed_users["teacher2"]))
    db.commit()
    params = {"month_label": "2026-09", "class_id": cls.id}
    assert client.get("/api/monthly-reports/writing-status", headers=auth("subject1"), params=params).json()["total"] == 0
    data = client.get("/api/monthly-reports/writing-status", headers=auth("teacher2"), params=params).json()
    assert data["total"] == 1 and data["items"][0]["subject"] == "数学"


def test_writing_status_authorization_and_invalid_filters(client, auth, db, seed_users):
    _, cls, other = _setup(db, seed_users)
    url = "/api/monthly-reports/writing-status"
    params = {"month_label": "2026-09"}
    for username in ("student1", "parent1", "admin", "deyu1"):
        assert client.get(url, headers=auth(username), params=params).status_code == 403
    headers = auth("subject1")
    assert client.get(url, headers=headers, params={**params, "class_id": other.id}).json()["total"] == 0
    assert client.get(url, headers=headers, params={"month_label": "2026-13"}).status_code == 400
    assert client.get(url, headers=headers, params={**params, "writing_status": "published"}).status_code == 422
    assert client.post("/api/monthly-reports", headers=headers, json={
        "student_id": seed_users["student1"], "class_id": cls.id, "month_label": "2026-09",
        "final_content": "代写德育", "evaluation_role": "head_teacher",
    }).status_code == 403


def test_writing_student_summary_counts_complete_duties_before_pagination(client, auth, db, seed_users):
    _, cls, _ = _setup(db, seed_users)
    db.add(ClassStudent(class_id=cls.id, student_id=seed_users["student3"]))
    db.add(ClassTeacher(class_id=cls.id, teacher_id=seed_users["teacher1"], role="subject_teacher", subject="英语"))
    from app.models.student_case import StudentCase, SubjectPlan
    for initial_case in db.query(StudentCase).filter_by(class_id=cls.id).all():
        db.add(SubjectPlan(student_case_id=initial_case.id, subject="英语", teacher_id=seed_users["teacher1"]))
    db.commit()
    _create_report(client, auth, cls, seed_users["student1"])
    headers = auth("teacher1")
    url = "/api/monthly-reports/writing-status"
    params = {"month_label": "2026-09", "view": "students", "limit": 1}
    data = client.get(url, headers=headers, params=params).json()
    assert data["student_total"] == 2
    assert data["items"] == []
    second = client.get(url, headers=headers, params={**params, "offset": 1}).json()
    students = data["students"] + second["students"]
    assert len({s["student_id"] for s in students}) == 2
    by_id = {s["student_id"]: s for s in students}
    assert (by_id[seed_users["student1"]]["written"], by_id[seed_users["student1"]]["unwritten"]) == (1, 2)
    assert by_id[seed_users["student3"]]["unwritten"] == 3
    filtered = client.get(url, headers=headers, params={**params, "writing_status": "written"}).json()
    assert filtered["student_total"] == 1
    assert filtered["students"][0]["unwritten"] == 2
    detail = client.get(url, headers=headers, params={
        "month_label": "2026-09", "class_id": cls.id, "student_id": seed_users["student1"],
    }).json()
    assert {r["subject"] for r in detail["items"]} == {"德育", "英语", "数学"}
    assert detail["written"] == 1 and detail["unwritten"] == 2


def test_head_sees_other_teachers_progress_without_edit_permission(client, auth, db, seed_users):
    subject, cls, other = _setup(db, seed_users)
    params = {"month_label": "2026-09", "class_id": cls.id}
    url = "/api/monthly-reports/writing-status"
    before = client.get(url, headers=auth("teacher1"), params=params).json()
    assert before["total"] == 2 and before["unwritten"] == 2
    assert {r["subject"] for r in before["items"]} == {"德育", "数学"}
    assert all(r["report_id"] is None for r in before["items"])
    report = _create_report(client, auth, cls, seed_users["student1"])
    assert client.put(f"/api/monthly-reports/{report['id']}/evaluation", headers=auth("subject1"), json={"content": "数学进步"}).status_code == 200
    after = client.get(url, headers=auth("teacher1"), params=params).json()
    math = next(r for r in after["items"] if r["subject"] == "数学")
    assert math["teacher_id"] == subject.id and math["teacher_name"] == subject.name
    assert math["writing_status"] == "written" and math["can_edit"] is False
    assert next(r for r in after["items"] if r["subject"] == "德育")["can_edit"] is True
    own = client.get(url, headers=auth("subject1"), params=params).json()
    assert len(own["items"]) == 1 and own["items"][0]["can_edit"] is True
    assert client.get(url, headers=auth("teacher2"), params=params).json()["total"] == 0
    assert client.put(f"/api/monthly-reports/{report['id']}/evaluation", headers=auth("teacher1"), json={"content": "代填数学", "teacher_id": subject.id}).status_code == 422


def test_deyu_subject_relation_is_not_a_second_monthly_duty(client, auth, db, seed_users):
    _, cls, _ = _setup(db, seed_users)
    db.add_all([
        ClassTeacher(class_id=cls.id, teacher_id=seed_users["teacher1"], role="subject_teacher", subject="德育"),
        ClassTeacher(class_id=cls.id, teacher_id=seed_users["teacher2"], role="subject_teacher", subject="德育"),
        ClassTeacher(class_id=cls.id, teacher_id=seed_users["teacher1"], role="subject_teacher", subject="英语"),
    ])
    db.commit()
    from app.models.student_case import StudentCase, SubjectPlan
    initial_case = db.query(StudentCase).filter_by(class_id=cls.id, student_id=seed_users["student1"]).one()
    db.add(SubjectPlan(student_case_id=initial_case.id, subject="英语", teacher_id=seed_users["teacher1"]))
    db.commit()
    report = _create_report(client, auth, cls, seed_users["student1"])
    data = client.get("/api/monthly-reports/writing-status", headers=auth("teacher1"), params={"month_label": "2026-09"}).json()
    assert [r["subject"] for r in data["items"]].count("德育") == 1
    assert {r["subject"] for r in data["items"]} == {"德育", "英语", "数学"}
    assert all("德育" not in r["subject"] for r in data["items"] if r["teacher_role"] == "subject_teacher")
    assert client.put(f"/api/monthly-reports/{report['id']}/evaluation", headers=auth("teacher2"), json={"content": "重复德育"}).status_code == 403


@pytest.mark.parametrize("teacher_name", ["", "政治老师"])
def test_initial_subject_without_linked_teacher_remains_visible(client, auth, db, seed_users, teacher_name):
    from datetime import date
    from app.models.student_case import CaseCycle, StudentCase, SubjectPlan
    _, cls, _ = _setup(db, seed_users)
    cycle = CaseCycle(name="初评缺任课关联", grade="高三", school_year="2026", starts_on=date(2026, 9, 1), ends_on=date(2027, 7, 1))
    db.add(cycle)
    db.flush()
    case = StudentCase(cycle_id=cycle.id, student_id=seed_users["student1"], class_id=cls.id, owner_teacher_id=seed_users["teacher1"])
    db.add(case)
    db.flush()
    db.add(SubjectPlan(student_case_id=case.id, subject="政治", teacher_id=seed_users["teacher1"], teacher_name=teacher_name, problem_location="初评政治信息"))
    db.commit()
    params = {"month_label": "2026-09", "student_id": seed_users["student1"]}
    data = client.get("/api/monthly-reports/writing-status", headers=auth("teacher1"), params=params).json()
    politics = next(r for r in data["items"] if r["subject"] == "政治")
    assert politics["assignment_required"] is True and politics["teacher_id"] is None
    assert politics["teacher_name"] == (teacher_name or "待确认任课老师")
    assert politics["can_edit"] is False and politics["writing_status"] == "unwritten"
    assert data["total"] == 2 and data["unwritten"] == 2
    moral = [r for r in data["items"] if r["subject"] == "德育"]
    assert len(moral) == 1 and moral[0]["teacher_role"] == "head_teacher"
    assert moral[0]["teacher_id"] == seed_users["teacher1"] and moral[0]["can_edit"] is True
    summary = client.get("/api/monthly-reports/writing-status", headers=auth("teacher1"), params={**params, "view": "students"}).json()
    assert summary["students"][0]["unwritten"] == 2
    # 展示初评科目不会给班主任或其他老师新增学科代填权限。
    assert client.post("/api/monthly-reports", headers=auth("teacher1"), json={"class_id": cls.id, "student_id": seed_users["student1"], "month_label": "2026-09", "evaluation_role": "subject_teacher", "final_content": "误代填政治"}).status_code == 403
    own = client.get("/api/monthly-reports/writing-status", headers=auth("subject1"), params=params).json()
    assert own["items"] == []


def test_monthly_subjects_equal_individual_initial_scope(client, auth, db, seed_users):
    from app.models.student_case import StudentCase, SubjectPlan
    _, cls, _ = _setup(db, seed_users)
    db.add(ClassStudent(class_id=cls.id, student_id=seed_users["student3"]))
    db.add(ClassTeacher(class_id=cls.id, teacher_id=seed_users["teacher2"], role="subject_teacher", subject="政治"))
    first = db.query(StudentCase).filter_by(student_id=seed_users["student1"], class_id=cls.id).one()
    second = db.query(StudentCase).filter_by(student_id=seed_users["student3"], class_id=cls.id).one()
    db.add(SubjectPlan(student_case_id=second.id, subject="政治", teacher_id=seed_users["teacher2"]))
    db.add(SubjectPlan(student_case_id=second.id, subject="英语", teacher_id=seed_users["teacher2"]))
    db.commit()
    url="/api/monthly-reports/writing-status"
    params={"month_label":"2026-09", "class_id":cls.id}
    for sid, expected in ((seed_users["student1"], {"德育","数学"}), (seed_users["student3"], {"德育","数学","政治","英语"})):
        data=client.get(url, headers=auth("teacher1"), params={**params,"student_id":sid}).json()
        assert {r["subject"] for r in data["items"]}==expected
        assert data["total"]==len(expected)
    assert client.get(url,headers=auth("teacher2"),params={**params,"student_id":seed_users["student1"]}).json()["total"]==0
    own=client.get(url,headers=auth("teacher2"),params={**params,"student_id":seed_users["student3"]}).json()
    assert {r["subject"] for r in own["items"]}=={"英语","政治"} and own["total"]==2
    db.add(ClassTeacher(class_id=cls.id,teacher_id=seed_users["teacher2"],role="subject_teacher",subject="数学"))
    db.commit()
    ambiguous=client.get(url,headers=auth("teacher1"),params={**params,"student_id":seed_users["student1"]}).json()
    assert ambiguous["total"]==2 and len([r for r in ambiguous["items"] if r["subject"]=="数学"])==1
    assert next(r for r in ambiguous["items"] if r["subject"]=="数学")["assignment_required"] is True
    db.query(SubjectPlan).filter_by(student_case_id=first.id).delete()
    db.commit()
    detail=client.get(url,headers=auth("teacher1"),params={**params,"student_id":seed_users["student1"]}).json()
    assert [r["subject"] for r in detail["items"]]==["德育"] and detail["total"]==1
    summary=client.get(url,headers=auth("teacher1"),params={**params,"view":"students"}).json()
    student=next(s for s in summary["students"] if s["student_id"]==seed_users["student1"])
    assert student["initial_required"] is True and student["total"]==1

    db.delete(first)
    db.commit()
    detail=client.get(url,headers=auth("teacher1"),params={**params,"student_id":seed_users["student1"]}).json()
    assert [r["subject"] for r in detail["items"]]==["德育"]
    assert client.post("/api/monthly-reports", headers=auth("subject1"), json={"class_id":cls.id,"student_id":seed_users["student1"],"month_label":"2026-09","final_content":"没有初评不能代建数学"}).status_code==403
