"""调班必须原子交接，且不能改写历史归属或扩大操作权限。"""
from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

from app.core.security import hash_password
from app.models.class_ import Class, ClassStudent, ClassTeacher, StudentGuardian, StudentConsultant
from app.models.class_transfer import ClassTransferBatch, ClassTransferItem
from app.models.monthly_report import MonthlyReport, MonthlyReportEvaluation
from app.models.student_case import CaseCycle, CaseReview, StudentCase, SubjectPlan, CaseTask, CaseVersion, CaseAuditLog
from app.models.user import User
from app.models.weekly_score import WeeklyTestScore

API = "/api/class-transfers"
NOW = datetime(2026, 10, 22, 4, 0, tzinfo=timezone.utc)


@pytest.fixture()
def transfer_roster(db, seed_users, monkeypatch):
    monkeypatch.setattr("app.services.class_transfer_service.school_now", lambda: NOW)
    password = hash_password("test123456")
    teachers = [User(username=name, name=name, role=role, password_hash=password) for name, role in (
        ("old_subject", "subject_teacher"), ("new_subject", "subject_teacher"), ("consultant", "consultant"))]
    db.add_all(teachers)
    db.flush()
    old, new, consultant = teachers
    source = Class(name="高三1班", grade="高三", school_year="2026-2027", teacher_id=seed_users["teacher1"])
    target = Class(name="高三2班", grade="高三", school_year="2026-2027", teacher_id=seed_users["teacher2"])
    course = Class(name="数学1V1", grade="高三", school_year="2026-2027", class_type="1V1", teacher_id=seed_users["teacher1"])
    db.add_all([source, target, course])
    db.flush()
    cycle = CaseCycle(name="本学年", grade="高三", school_year="2026-2027", starts_on=date(2026, 8, 1), ends_on=date(2027, 7, 31))
    db.add(cycle)
    db.flush()
    cases = []
    for i in (1, 2):
        sid = seed_users[f"student{i}"]
        db.add(ClassStudent(class_id=source.id, student_id=sid, joined_at=datetime(2026, 8, 1, tzinfo=timezone.utc)))
        case = StudentCase(cycle_id=cycle.id, student_id=sid, class_id=source.id, owner_teacher_id=seed_users["teacher1"], status="draft")
        db.add(case)
        db.flush()
        db.add_all([SubjectPlan(student_case_id=case.id, subject="数学", teacher_id=old.id, teacher_name=old.name),
            SubjectPlan(student_case_id=case.id, subject="德育", teacher_id=seed_users["teacher1"], teacher_name="原班主任")])
        cases.append(case)
    db.add_all([ClassTeacher(class_id=source.id, teacher_id=old.id, role="subject_teacher", subject="数学"),
        ClassTeacher(class_id=target.id, teacher_id=new.id, role="subject_teacher", subject="数学"),
        ClassStudent(class_id=course.id, student_id=seed_users["student1"]),
        StudentGuardian(parent_id=seed_users["parent1"], student_id=seed_users["student1"]),
        StudentConsultant(consultant_id=consultant.id, student_id=seed_users["student1"])])
    reports = []
    for sid, case, month, status in (
        (seed_users["student1"], cases[0], "2026-09", "published"),
        (seed_users["student1"], cases[0], "2026-10", "generated"),
        (seed_users["student2"], cases[1], "2026-10", "published")):
        report = MonthlyReport(student_id=sid, class_id=source.id, student_case_id=case.id, month_label=month,
            period_start=date.fromisoformat(month + "-01"), period_end=date.fromisoformat(month + "-28"), status=status,
            final_content="原班主任填写的内容", reviewed_by=seed_users["teacher1"])
        db.add(report)
        db.flush()
        db.add(MonthlyReportEvaluation(report_id=report.id, teacher_id=old.id, teacher_name=old.name,
            teacher_role="subject_teacher", subject="数学", content="原数学老师的评定"))
        reports.append(report)
    score = WeeklyTestScore(class_id=source.id, student_id=seed_users["student1"], subject="数学", exam_month="2026-09",
        exam_date=date(2026, 9, 20), score=80, max_score=100, recorded_by=seed_users["teacher1"])
    review = CaseReview(student_case_id=cases[0].id, review_level="deyu", reviewer_id=seed_users["deyu1"],
        assigned_to=seed_users["teacher1"], workflow_status="open", visibility="internal")
    task = CaseTask(student_case_id=cases[0].id, subject="数学", title="继续练习", cadence="daily",
        starts_on=date(2026, 10, 1), due_on=date(2026, 11, 1), created_by=seed_users["teacher1"])
    version = CaseVersion(student_case_id=cases[0].id, version=1, snapshot={"original_class": source.id}, created_by=seed_users["teacher1"])
    db.add_all([score, review, task, version])
    db.commit()
    return dict(source=source.id, target=target.id, course=course.id, cases=[c.id for c in cases],
        old=old.id, new=new.id, reports=[r.id for r in reports], score=score.id, review=review.id, task=task.id, version=version.id)


def rows_for(roster, *names):
    return [dict(student_username=name, source_class_id=roster["source"], target_class_id=roster["target"]) for name in names or ("student1",)]


def commit(client, headers, rows, **extra):
    preview = client.post(API + "/preview", headers=headers, json={"rows": rows})
    assert preview.status_code == 200, preview.text
    assert preview.json()["valid"], preview.text
    payload = dict(rows=rows, reason="年级重新分班", preview_token=preview.json()["preview_token"], request_id=str(uuid4()), **extra)
    response = client.post(API, headers=headers, json=payload)
    return response, payload


@pytest.mark.parametrize("name", ["teacher1", "old_subject", "consultant", "student1", "parent1"])
def test_transfer_interfaces_reject_other_roles(client, auth, transfer_roster, name):
    headers = auth(name)
    rows = rows_for(transfer_roster)
    assert client.get(API, headers=headers).status_code == 403
    assert client.post(API + "/preview", headers=headers, json={"rows": rows}).status_code == 403
    assert client.post(API, headers=headers, json=dict(rows=rows, reason="重新分班", preview_token="a" * 64, request_id=str(uuid4()))).status_code == 403


@pytest.mark.parametrize("manager", ["admin", "deyu1"])
def test_atomic_handover_and_replay(client, auth, db, seed_users, transfer_roster, manager):
    r = transfer_roster
    before = client.get("/api/monthly-reports/writing-status?month_label=2026-09&class_id=" + str(r["source"]), headers=auth("admin")).json()
    headers = auth(manager)
    response, payload = commit(client, headers, rows_for(r, "student1", "student2"))
    assert response.status_code == 200, response.text
    assert response.json()["student_count"] == 2
    assert client.post(API, headers=headers, json=payload).json()["id"] == response.json()["id"]
    changed_payload = {**payload, "reason": "另一个调班原因"}
    assert client.post(API, headers=headers, json=changed_payload).status_code == 409
    db.expire_all()
    assert db.query(ClassTransferBatch).count() == 1 and db.query(ClassTransferItem).count() == 2
    assert db.query(ClassStudent).filter_by(class_id=r["source"]).count() == 0
    assert db.query(ClassStudent).filter_by(class_id=r["target"]).count() == 2
    assert db.query(ClassStudent).filter_by(class_id=r["course"], student_id=seed_users["student1"]).count() == 1
    assert db.get(StudentCase, r["cases"][0]).owner_teacher_id == seed_users["teacher2"]
    assert db.query(SubjectPlan).filter_by(student_case_id=r["cases"][0], subject="数学").one().teacher_id == r["new"]
    assert db.get(CaseReview, r["review"]).assigned_to == seed_users["teacher2"]
    assert db.get(CaseTask, r["task"]).title == "继续练习"
    assert db.get(CaseVersion, r["version"]).snapshot == {"original_class": r["source"]}
    assert db.get(User, seed_users["student1"]).username == "student1"
    assert db.query(StudentGuardian).count() == 1 and db.query(StudentConsultant).count() == 1
    assert db.get(MonthlyReport, r["reports"][0]).class_id == r["source"]
    assert db.get(MonthlyReport, r["reports"][1]).class_id == r["target"]
    assert db.get(MonthlyReport, r["reports"][1]).final_content == "原班主任填写的内容"
    assert db.get(MonthlyReport, r["reports"][2]).class_id == r["source"]
    assert db.get(WeeklyTestScore, r["score"]).class_id == r["source"]
    assert db.get(WeeklyTestScore, r["score"]).study_subjects_snapshot == ["数学"]
    assert db.query(CaseAuditLog).filter_by(action="case.class_transferred").count() == 2
    after = client.get("/api/monthly-reports/writing-status?month_label=2026-09&class_id=" + str(r["source"]), headers=auth("admin")).json()
    assert (before["total"], before["written"], before["unwritten"]) == (after["total"], after["written"], after["unwritten"])
    current = client.get("/api/monthly-reports/writing-status?month_label=2026-10&class_id=" + str(r["target"]), headers=auth("teacher2")).json()
    assert current["total"] == 4 and current["written"] == 4, current
    old = auth("old_subject")
    assert client.get(f"/api/student-cases/{r['cases'][0]}", headers=old).status_code == 403
    assert client.get("/api/student-cases/subject-plan-reminders", headers=old).json()["total"] == 0
    assert client.get(f"/api/student-cases/{r['cases'][0]}", headers=auth("new_subject")).status_code == 200
    assert client.get(f"/api/monthly-reports/{r['reports'][0]}", headers=auth("teacher2")).status_code == 200
    assert client.get(f"/api/monthly-reports/{r['reports'][0]}", headers=auth("parent1")).status_code == 200
    history = client.get(API, headers=headers).json()
    assert history["total"] == 1 and history["items"][0]["reason"] == "年级重新分班"
    assert client.delete(f"/api/classes/{r['source']}", headers=headers).status_code == 409
    overview = client.get("/api/monthly-exam-scores/overview?exam_month=2026-09", headers=auth("admin")).json()
    assert overview["items"][0]["total_score"] == 80 and overview["items"][0]["complete"]
    new_head_overview = client.get("/api/monthly-exam-scores/overview?exam_month=2026-09", headers=auth("teacher2")).json()
    assert new_head_overview["items"][0]["total_score"] == 80


def test_validation_and_stale_preview_do_not_partially_move(client, auth, db, seed_users, transfer_roster):
    r, headers = transfer_roster, auth("deyu1")
    rows = rows_for(r) + [dict(student_username="missing", target_class_id=r["target"])]
    preview = client.post(API + "/preview", headers=headers, json={"rows": rows}).json()
    assert not preview["valid"] and preview["rows"][1]["errors"]
    denied = client.post(API, headers=headers, json=dict(rows=rows, reason="调整", preview_token=preview["preview_token"], request_id=str(uuid4())))
    assert denied.status_code == 409
    rows = rows_for(r)
    preview = client.post(API + "/preview", headers=headers, json={"rows": rows}).json()
    plan = db.query(SubjectPlan).filter_by(student_case_id=r["cases"][0], subject="数学").one()
    plan.problem_location = "预览后老师保存的新内容"
    db.commit()
    denied = client.post(API, headers=headers, json=dict(rows=rows, reason="调整", preview_token=preview["preview_token"], request_id=str(uuid4())))
    assert denied.status_code == 409
    db.expire_all()
    assert db.query(ClassTransferBatch).count() == 0
    assert db.query(ClassStudent).filter_by(class_id=r["source"], student_id=seed_users["student1"]).first()
    duplicate = client.post(API + "/preview", headers=headers, json={"rows": rows * 2}).json()
    assert not duplicate["valid"]


def test_ambiguous_teacher_requires_explicit_assignment(client, auth, db, seed_users, transfer_roster):
    r, headers = transfer_roster, auth("admin")
    db.add(ClassTeacher(class_id=r["target"], teacher_id=seed_users["teacher2"], role="subject_teacher", subject="数学"))
    db.commit()
    rows = rows_for(r)
    preview = client.post(API + "/preview", headers=headers, json={"rows": rows}).json()
    assert not preview["valid"]
    rows[0]["subject_teachers"] = {"数学": r["new"]}
    response, _ = commit(client, headers, rows)
    assert response.status_code == 200, response.text


def test_enrollment_cannot_bypass_transfer(client, auth, db, seed_users, transfer_roster):
    for name in ("teacher2", "consultant", "deyu1", "admin"):
        response = client.post(f"/api/classes/{transfer_roster['target']}/students", headers=auth(name), json={"student_ids": [seed_users["student3"], seed_users["student1"]]})
        assert response.status_code == 409, response.text
    assert not db.query(ClassStudent).filter_by(class_id=transfer_roster["target"]).first()


def test_published_history_read_only_for_both_heads(client, auth, transfer_roster):
    r = transfer_roster
    response, _ = commit(client, auth("deyu1"), rows_for(r, "student1", "student2"))
    assert response.status_code == 200, response.text
    for name in ("teacher1", "teacher2", "admin"):
        headers = auth(name)
        report = client.get(f"/api/monthly-reports/{r['reports'][2]}", headers=headers)
        assert report.status_code == 200, report.text
        assert not report.json()["can_manage"] and not report.json()["can_evaluate"] and not report.json()["can_publish"]
        assert client.put(f"/api/monthly-reports/{r['reports'][2]}", headers=headers, json={"final_content": "不能覆盖历史"}).status_code == 409
    repeat = client.post("/api/monthly-reports", headers=auth("teacher2"), json=dict(student_id=response.json()["items"][1]["student_id"], class_id=r["target"], month_label="2026-10", final_content="不要重复创建"))
    assert repeat.status_code == 409


def test_cross_grade_and_missing_teacher_blocked(client, auth, db, transfer_roster):
    r = transfer_roster
    cls = db.get(Class, r["target"])
    cls.grade = "高二"
    db.commit()
    preview = client.post(API + "/preview", headers=auth("admin"), json={"rows": rows_for(r)}).json()
    assert not preview["valid"]
    cls.grade = "高三"
    db.query(ClassTeacher).filter_by(class_id=r["target"]).delete()
    db.commit()
    preview = client.post(API + "/preview", headers=auth("admin"), json={"rows": rows_for(r)}).json()
    assert not preview["valid"] and any("数学" in err for err in preview["rows"][0]["errors"])


def test_swapping_classes_preserves_counts(client, auth, db, seed_users, transfer_roster):
    r = transfer_roster
    member = db.query(ClassStudent).filter_by(student_id=seed_users["student2"], class_id=r["source"]).one()
    member.class_id = r["target"]
    case = db.get(StudentCase, r["cases"][1])
    case.class_id, case.owner_teacher_id = r["target"], seed_users["teacher2"]
    for p in db.query(SubjectPlan).filter_by(student_case_id=case.id):
        p.teacher_id = r["new"] if p.subject == "数学" else seed_users["teacher2"]
    db.get(MonthlyReport, r["reports"][2]).class_id = r["target"]
    db.commit()
    rows = rows_for(r) + [dict(student_username="student2", source_class_id=r["target"], target_class_id=r["source"])]
    headers = auth("admin")
    preview = client.post(API + "/preview", headers=headers, json={"rows": rows}).json()
    assert preview["valid"] and all(c["before"] == c["after"] == 1 for c in preview["classes"]), preview
    response, _ = commit(client, headers, rows)
    assert response.status_code == 200, response.text
    db.expire_all()
    assert db.query(ClassStudent).filter_by(class_id=r["source"], student_id=seed_users["student2"]).first()
    assert db.query(ClassStudent).filter_by(class_id=r["target"], student_id=seed_users["student1"]).first()


def test_late_failure_rolls_back_whole_batch(client, auth, db, seed_users, transfer_roster, monkeypatch):
    from fastapi import HTTPException
    from app.services import class_transfer_service as service
    original = service.audit
    count = 0
    def fail_second_case(*args, **kwargs):
        nonlocal count
        if args[2] == "case.class_transferred":
            count += 1
            if count == 2:
                raise HTTPException(409, "模拟第二名学生交接失败")
        return original(*args, **kwargs)
    monkeypatch.setattr(service, "audit", fail_second_case)
    response, _ = commit(client, auth("admin"), rows_for(transfer_roster, "student1", "student2"))
    assert response.status_code == 409
    db.expire_all()
    assert db.query(ClassTransferBatch).count() == 0 and db.query(ClassTransferItem).count() == 0
    assert db.query(ClassStudent).filter_by(class_id=transfer_roster["source"]).count() == 2
    assert db.get(StudentCase, transfer_roster["cases"][0]).owner_teacher_id == seed_users["teacher1"]


def test_concurrent_managers_cannot_transfer_twice(client, auth, db, transfer_roster):
    from concurrent.futures import ThreadPoolExecutor
    rows = rows_for(transfer_roster)
    headers = [auth("admin"), auth("deyu1")]
    preview = client.post(API + "/preview", headers=headers[0], json={"rows": rows}).json()
    payloads = [dict(rows=rows, reason="并发调班验证", request_id=str(uuid4()), preview_token=preview["preview_token"]) for _ in headers]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(client.post, API, headers=h, json=p) for h, p in zip(headers, payloads)]
        responses = [future.result(timeout=30) for future in futures]
    assert sorted(r.status_code for r in responses) == [200, 409], [r.text for r in responses]
    db.expire_all()
    assert db.query(ClassTransferBatch).count() == 1 and db.query(ClassTransferItem).count() == 1


def test_historical_points_and_archived_case_remain_readable(client, auth, db, seed_users, transfer_roster):
    from app.models.case_points import StudentPointsReport
    r = transfer_roster
    old_cycle = CaseCycle(name="旧周期", school_year="2025-2026", grade="高三", starts_on=date(2025, 8, 1), ends_on=date(2026, 7, 31), is_active=False)
    db.add(old_cycle)
    db.flush()
    archived = StudentCase(cycle_id=old_cycle.id, student_id=seed_users["student1"], class_id=r["source"], owner_teacher_id=seed_users["teacher1"], status="archived")
    points = StudentPointsReport(student_id=seed_users["student1"], class_id=r["source"], student_case_id=r["cases"][0],
        period_type="monthly", period_label="2026-09", period_start=date(2026, 9, 1), period_end=date(2026, 9, 30),
        earned_points=18, total_points=30, detail={"original": True})
    db.add_all([archived, points])
    db.commit()
    archived_id, points_id = archived.id, points.id
    response, _ = commit(client, auth("deyu1"), rows_for(r))
    assert response.status_code == 200, response.text
    db.expire_all()
    assert db.get(StudentCase, archived_id).class_id == r["source"]
    assert client.get(f"/api/student-cases/{archived_id}", headers=auth("teacher2")).status_code == 200
    archived_list = client.get("/api/student-cases?status=archived", headers=auth("teacher2")).json()
    assert archived_id in {c["id"] for c in archived_list}
    reports = client.get(f"/api/points-reports?class_id={r['target']}", headers=auth("teacher2")).json()
    assert reports[0]["id"] == points_id and reports[0]["class_id"] == r["source"]
    rebuilt = client.post("/api/points-reports/build", headers=auth("teacher1"), json=dict(class_id=r["source"], period_type="monthly", period_label="2026-09"))
    assert rebuilt.status_code == 200, rebuilt.text
    db.expire_all()
    points = db.get(StudentPointsReport, points_id)
    assert points.class_id == r["source"] and points.earned_points == 18 and points.total_points == 30 and points.detail == {"original": True}
