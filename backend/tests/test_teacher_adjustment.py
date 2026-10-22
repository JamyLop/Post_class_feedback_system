"""管理员换师的交接范围、权限、历史保留和冲突验证。"""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.monthly_reports import _evaluation_role
from app.core.security import hash_password
from app.models.class_ import Class, ClassStudent, ClassTeacher
from app.models.monthly_report import MonthlyReport, MonthlyReportEvaluation
from app.models.student_case import CaseAuditLog, CaseCycle, CaseVersion, StudentCase, SubjectPlan
from app.models.user import User


@pytest.fixture()
def scope(db, seed_users):
    password = hash_password("test123456")
    users = {}
    for name, role in [("old_subject", "subject_teacher"), ("new_subject", "subject_teacher"),
                       ("other_subject", "subject_teacher"), ("student4", "student"), ("student5", "student")]:
        users[name] = User(username=name, name=name, role=role, password_hash=password)
        db.add(users[name])
    db.flush()
    cls = Class(name="交接班级", grade="高三", teacher_id=seed_users["teacher1"])
    other_cls = Class(name="无关班级", grade="高三", teacher_id=seed_users["teacher2"])
    active = CaseCycle(name="在用周期", school_year="2026-2027", starts_on=date(2026, 8, 1), ends_on=date(2027, 7, 31))
    inactive = CaseCycle(name="停用周期", school_year="2025-2026", starts_on=date(2025, 8, 1), ends_on=date(2026, 7, 31), is_active=False)
    db.add_all([cls, other_cls, active, inactive])
    db.flush()
    link = ClassTeacher(class_id=cls.id, teacher_id=users["old_subject"].id, subject="数学", role="subject_teacher")
    db.add_all([link,
        ClassTeacher(class_id=cls.id, teacher_id=users["old_subject"].id, subject="英语", role="subject_teacher"),
        ClassTeacher(class_id=other_cls.id, teacher_id=users["old_subject"].id, subject="数学", role="subject_teacher"),
        ClassTeacher(class_id=cls.id, teacher_id=users["other_subject"].id, subject="数学", role="subject_teacher"),
    ])
    cases, plans = {}, {}
    for key, sid, status, cycle, classroom, teacher in [
        ("draft", seed_users["student1"], "draft", active, cls, users["old_subject"]),
        ("executing", seed_users["student2"], "executing", active, cls, users["old_subject"]),
        ("archived", seed_users["student3"], "archived", active, cls, users["old_subject"]),
        ("inactive", seed_users["student1"], "draft", inactive, cls, users["old_subject"]),
        ("other_class", users["student4"].id, "draft", active, other_cls, users["old_subject"]),
        ("other_teacher", users["student5"].id, "draft", active, cls, users["other_subject"]),
    ]:
        case = StudentCase(student_id=sid, cycle_id=cycle.id, class_id=classroom.id,
                           owner_teacher_id=classroom.teacher_id, status=status)
        db.add(case)
        db.flush()
        plan = SubjectPlan(student_case_id=case.id, subject="数学", teacher_id=teacher.id,
                           teacher_name=teacher.name, problem_location="保留诊断", cause_analysis="保留分析",
                           reinforcement="保留措施", status="draft")
        db.add(plan)
        cases[key], plans[key] = case, plan
        if key != "inactive":
            db.add(ClassStudent(class_id=classroom.id, student_id=sid))
    for subject in ("英语", "德育"):
        plan = SubjectPlan(student_case_id=cases["draft"].id, subject=subject,
                           teacher_id=users["old_subject"].id, teacher_name=users["old_subject"].name)
        db.add(plan)
        plans[subject] = plan
    report = MonthlyReport(student_id=seed_users["student1"], class_id=cls.id, student_case_id=cases["draft"].id,
                           month_label="2026-09", period_start=date(2026, 9, 1), period_end=date(2026, 9, 30),
                           status="published", final_content="历史月评内容")
    db.add(report)
    db.flush()
    evaluation = MonthlyReportEvaluation(report_id=report.id, teacher_id=users["old_subject"].id,
        teacher_name="历史原老师", teacher_role="subject_teacher", subject="数学", content="历史学科评价")
    version = CaseVersion(student_case_id=cases["draft"].id, version=1,
                          snapshot={"subject_plans": [{"teacher_id": users["old_subject"].id}]},
                          created_by=seed_users["teacher1"])
    db.add_all([evaluation, version])
    db.commit()
    return dict(users=users, cls=cls, other_cls=other_cls, link=link, cases=cases, plans=plans,
                report=report, evaluation=evaluation, version=version)


def _body(scope, **overrides):
    return dict(teacher_id=scope["users"]["new_subject"].id,
                previous_teacher_id=scope["users"]["old_subject"].id, reason=" 教学安排调整 ", **overrides)


def test_adjust_teacher_handoff_scope_and_history(client, auth, db, scope, seed_users):
    old_id, new_id = scope["users"]["old_subject"].id, scope["users"]["new_subject"].id
    untouched = {key: (plan.teacher_id, plan.teacher_name) for key, plan in scope["plans"].items()
                 if key not in {"draft", "executing"}}
    response = client.put(f'/api/admin/class-teacher-links/{scope["link"].id}', headers=auth("admin"), json=_body(scope))
    assert response.status_code == 200, response.text
    assert response.json()["teacher_id"] == new_id
    assert response.json()["updated_plans"] == 2
    db.expire_all()
    for key in ("draft", "executing"):
        plan = scope["plans"][key]
        assert (plan.teacher_id, plan.teacher_name) == (new_id, "new_subject")
        assert (plan.problem_location, plan.cause_analysis, plan.reinforcement, plan.status) == (
            "保留诊断", "保留分析", "保留措施", "draft")
    for key, original in untouched.items():
        assert (scope["plans"][key].teacher_id, scope["plans"][key].teacher_name) == original
    assert scope["cases"]["executing"].status == "executing"
    assert scope["cases"]["draft"].owner_teacher_id == seed_users["teacher1"]
    assert scope["report"].final_content == "历史月评内容"
    assert (scope["evaluation"].teacher_id, scope["evaluation"].teacher_name, scope["evaluation"].content) == (old_id, "历史原老师", "历史学科评价")
    assert scope["version"].snapshot == {"subject_plans": [{"teacher_id": old_id}]}
    log = db.query(CaseAuditLog).filter_by(action="class_teacher.adjusted").one()
    assert log.actor_id == seed_users["admin"]
    assert log.detail["reason"] == "教学安排调整"
    assert log.detail["previous_teacher_id"] == old_id
    assert log.detail["updated_plans"] == 2
    assert db.query(CaseAuditLog).filter_by(action="subject_plan.assigned").count() == 2
    assert _evaluation_role(db, scope["report"], scope["users"]["new_subject"]) == ("subject_teacher", "数学")
    assert "数学" not in (_evaluation_role(db, scope["report"], scope["users"]["old_subject"]) or ("", ""))[1]
    new_classes = client.get("/api/classes", headers=auth("new_subject")).json()
    assert {row["id"] for row in new_classes} == {scope["cls"].id}
    reminders = client.get('/api/student-cases/subject-plan-reminders', headers=auth("new_subject")).json()
    assert {row["plan_id"] for row in reminders["items"]} == {scope["plans"]["draft"].id}
    url = f'/api/student-cases/{scope["cases"]["draft"].id}/subject-plans/数学'
    body = {"subject": "数学", "teacher_id": old_id, "reinforcement": "旧老师越权"}
    assert client.put(url, headers=auth("old_subject"), json=body).status_code == 403
    body.update(teacher_id=new_id, reinforcement="接任老师继续填写")
    result = client.put(url, headers=auth("new_subject"), json=body)
    assert result.status_code == 200, result.text
    reminders = client.get('/api/student-cases/subject-plan-reminders', headers=auth("new_subject")).json()
    assert reminders["total"] == 0


@pytest.mark.parametrize("username", ["teacher1", "old_subject", "deyu1", "parent1", "student1"])
def test_adjust_teacher_admin_only(client, auth, db, scope, username):
    result = client.put(f'/api/admin/class-teacher-links/{scope["link"].id}', headers=auth(username), json=_body(scope))
    assert result.status_code == 403
    db.refresh(scope["link"])
    assert scope["link"].teacher_id == scope["users"]["old_subject"].id


@pytest.mark.parametrize("invalid", ["disabled", "student", "missing", "same", "stale", "duplicate", "head", "deyu"])
def test_adjust_teacher_rejects_invalid_and_stale_requests(client, auth, db, scope, seed_users, invalid):
    body = _body(scope)
    expected = 400
    if invalid == "disabled":
        scope["users"]["new_subject"].status = "disabled"
    elif invalid == "student":
        body["teacher_id"] = seed_users["student1"]
    elif invalid == "missing":
        body["teacher_id"] = 999999
    elif invalid == "same":
        body["teacher_id"] = body["previous_teacher_id"]
    elif invalid == "stale":
        body["previous_teacher_id"] = seed_users["teacher2"]
        expected = 409
    elif invalid == "duplicate":
        body["teacher_id"] = scope["users"]["other_subject"].id
        expected = 409
    elif invalid == "head":
        scope["link"].role = "head_teacher"
    elif invalid == "deyu":
        scope["link"].subject = "德育"
    db.commit()
    response = client.put(f'/api/admin/class-teacher-links/{scope["link"].id}', headers=auth("admin"), json=body)
    assert response.status_code == expected, response.text
    db.expire_all()
    assert scope["plans"]["draft"].teacher_id == scope["users"]["old_subject"].id
    assert db.query(CaseAuditLog).filter_by(action="class_teacher.adjusted").count() == 0


def test_adjust_teacher_missing_link_and_repeated_request(client, auth, db, scope):
    headers, body = auth("admin"), _body(scope)
    assert client.put('/api/admin/class-teacher-links/999999', headers=headers, json=body).status_code == 404
    url = f'/api/admin/class-teacher-links/{scope["link"].id}'
    assert client.put(url, headers=headers, json=body).status_code == 200
    assert client.put(url, headers=headers, json=body).status_code == 409
    assert db.query(CaseAuditLog).filter_by(action="class_teacher.adjusted").count() == 1


def test_adjust_teacher_accepts_head_teacher_dual_teaching(client, auth, db, scope, seed_users):
    body = _body(scope)
    body["teacher_id"] = seed_users["teacher1"]
    response = client.put(f'/api/admin/class-teacher-links/{scope["link"].id}', headers=auth("admin"), json=body)
    assert response.status_code == 200, response.text
    db.expire_all()
    assert scope["link"].role == "subject_teacher"
    assert scope["cls"].teacher_id == seed_users["teacher1"]


def test_adjust_teacher_without_plans_and_requires_stale_guard(client, auth, db, scope):
    link = ClassTeacher(class_id=scope["cls"].id, teacher_id=scope["users"]["old_subject"].id,
                        subject="物理", role="subject_teacher")
    db.add(link)
    db.commit()
    url, headers = f"/api/admin/class-teacher-links/{link.id}", auth("admin")
    body = _body(scope)
    missing_guard = {key: value for key, value in body.items() if key != "previous_teacher_id"}
    assert client.put(url, headers=headers, json=missing_guard).status_code == 422
    body["reason"] = "x" * 501
    assert client.put(url, headers=headers, json=body).status_code == 422
    body["reason"] = ""
    result = client.put(url, headers=headers, json=body)
    assert result.status_code == 200, result.text
    assert result.json()["updated_plans"] == 0


def test_adjust_teacher_commit_failure_rolls_back_entire_handoff(client, auth, db, scope, monkeypatch):
    headers = auth("admin")
    def conflict(session):
        session.flush()
        raise IntegrityError("simulated uniqueness conflict", {}, Exception("conflict"))
    with monkeypatch.context() as patch:
        patch.setattr(Session, "commit", conflict)
        result = client.put(f'/api/admin/class-teacher-links/{scope["link"].id}', headers=headers, json=_body(scope))
    assert result.status_code == 409, result.text
    db.expire_all()
    assert scope["link"].teacher_id == scope["users"]["old_subject"].id
    assert scope["plans"]["draft"].teacher_id == scope["users"]["old_subject"].id
    assert db.query(CaseAuditLog).filter(CaseAuditLog.action.in_(["class_teacher.adjusted", "subject_plan.assigned"])).count() == 0


def test_adjust_teacher_concurrent_admins_cannot_overwrite(client, auth, db, scope, seed_users):
    headers, barrier = auth("admin"), Barrier(2)
    base, link_id = _body(scope), scope["link"].id
    choices = [scope["users"]["new_subject"].id, seed_users["teacher2"]]
    def adjust(teacher_id):
        body = dict(base)
        body["teacher_id"] = teacher_id
        barrier.wait(timeout=10)
        return client.put(f'/api/admin/class-teacher-links/{link_id}', headers=headers, json=body).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(adjust, choices))
    assert sorted(results) == [200, 409]
    db.expire_all()
    assert scope["link"].teacher_id in choices
    assert scope["plans"]["draft"].teacher_id == scope["link"].teacher_id
    assert db.query(CaseAuditLog).filter_by(action="class_teacher.adjusted").count() == 1
