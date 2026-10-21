"""主管身份的授予、撤销、学段隔离和写权限回归。"""
from datetime import date

import pytest

from app.core.security import hash_password
from app.models.class_ import Class, ClassStudent, ClassTeacher
from app.models.monthly_report import MonthlyReport, MonthlyReportEvaluation
from app.models.student_case import CaseCycle, StudentCase, SubjectPlan, CaseAuditLog
from app.models.user import User
from app.models.weekly_score import WeeklyTestScore


@pytest.fixture()
def supervision_data(db, seed_users):
    manager = User(username="stage-manager", name="学段主管", role="subject_teacher", password_hash=hash_password("test123456"))
    regular = User(username="stage-regular", name="普通任课老师", role="subject_teacher", password_hash=hash_password("test123456"))
    db.add_all([manager, regular]); db.flush()
    cycle = CaseCycle(name="测试周期", school_year="2026-2027", starts_on=date(2026, 8, 1), ends_on=date(2027, 7, 31))
    db.add(cycle); db.flush()
    classes, reports, cases, scores = [], [], [], []
    for index, (stage, grade) in enumerate([("初中", "初三"), ("高中", "高三")]):
        cls = Class(name=f"{stage}测试班", education_stage=stage, grade=grade, teacher_id=seed_users["teacher1"])
        db.add(cls); db.flush(); classes.append(cls.id)
        sid = seed_users[f"student{index + 1}"]
        db.add(ClassStudent(class_id=cls.id, student_id=sid))
        case = StudentCase(cycle_id=cycle.id, class_id=cls.id, student_id=sid, owner_teacher_id=seed_users["teacher1"])
        db.add(case); db.flush(); cases.append(case.id)
        db.add(SubjectPlan(student_case_id=case.id, subject="数学", teacher_id=regular.id, teacher_name=regular.name))
        report = MonthlyReport(student_id=sid, class_id=cls.id, student_case_id=case.id, month_label="2026-10",
                               period_start=date(2026, 10, 1), period_end=date(2026, 10, 31),
                               status="generated", final_content="德育已填写")
        db.add(report); db.flush(); reports.append(report.id)
        db.add(MonthlyReportEvaluation(report_id=report.id, teacher_id=regular.id, teacher_name=regular.name,
                                      teacher_role="subject_teacher", subject="数学", content="学科已填写"))
        score = WeeklyTestScore(student_id=sid, class_id=cls.id, subject="数学", exam_month="2026-10",
                                exam_date=date(2026, 10, 10), exam_name="十月月考", score=80 + index,
                                max_score=100, recorded_by=seed_users["teacher1"])
        db.add(score); db.flush(); scores.append(score.id)
    # 主管还在高中任教：专门检查初中主管视图不能混入跨学段任课数据。
    db.add(ClassTeacher(class_id=classes[1], teacher_id=manager.id, role="subject_teacher", subject="数学"))
    db.commit()
    return dict(manager=manager.id, regular=regular.id, classes=classes, reports=reports, cases=cases, scores=scores)


@pytest.mark.parametrize("stage,index", [("初中", 0), ("高中", 1)])
def test_supervisor_stage_scope_and_read_only(client, auth, db, supervision_data, stage, index):
    data = supervision_data
    admin, supervisor = auth("admin"), auth("stage-manager")
    response = client.put(f"/api/users/{data['manager']}/supervisor", headers=admin, json={"stage": stage})
    assert response.status_code == 200, response.text
    assert response.json()["role"] == "subject_teacher"
    assert client.get("/api/auth/me", headers=supervisor).json()["supervisor_stage"] == stage
    classes = client.get("/api/users/supervision-classes", headers=supervisor)
    assert classes.status_code == 200 and [c["id"] for c in classes.json()] == [data["classes"][index]]
    params = {"scope": "supervision", "month_label": "2026-10"}
    response = client.get("/api/monthly-reports/writing-status", headers=supervisor, params=params)
    assert response.status_code == 200, response.text
    rows = response.json()["items"]
    assert len(rows) == 2 and {r["class_id"] for r in rows} == {data["classes"][index]}
    assert {r["teacher_id"] for r in rows} == {data["regular"], db.get(Class, data["classes"][index]).teacher_id}
    assert all(r["can_edit"] is False for r in rows)
    # 日常任课页面同样能看到本学段其他老师的进度与评定，但不混入其他学段。
    daily = client.get("/api/monthly-reports/writing-status", headers=supervisor,
                       params={"month_label": "2026-10"}).json()
    assert {r["class_id"] for r in daily["items"]} == {data["classes"][index]}
    assert {r["teacher_id"] for r in daily["items"]} == {data["regular"], db.get(Class, data["classes"][index]).teacher_id}
    listing = client.get("/api/monthly-reports", headers=supervisor,
                         params={"month_label": "2026-10"}).json()
    assert data["classes"][index] in {r["class_id"] for r in listing}
    assert data["reports"][index] in {r["id"] for r in listing}
    opposite = client.get("/api/monthly-reports/writing-status", headers=supervisor,
                          params={**params, "class_id": data["classes"][1-index]}).json()
    assert opposite["items"] == [] and opposite["total"] == 0
    overview = client.get("/api/monthly-exam-scores/overview", headers=supervisor, params={"scope": "supervision"})
    assert overview.status_code == 200, overview.text
    result = overview.json()
    assert result["total"] == 1 and result["items"][0]["class_id"] == data["classes"][index]
    assert result["items"][0]["can_view_total"] is True
    assert result["items"][0]["total_score"] == 80 + index
    assert client.get(f"/api/monthly-reports/{data['reports'][index]}", headers=supervisor).status_code == 200
    # 初中班与主管没有任课关系；主管权限不能用于代填、发布、改分或改档案。
    if index == 0:
        for method, url, payload in [
            ("put", f"/api/monthly-reports/{data['reports'][0]}", {"final_content": "代填"}),
            ("put", f"/api/monthly-reports/{data['reports'][0]}/evaluation", {"content": "代填"}),
            ("post", f"/api/monthly-reports/{data['reports'][0]}/publish", {}),
            ("patch", f"/api/student-cases/{data['cases'][0]}", {"overall_problem": "篡改"}),
            ("put", f"/api/monthly-exam-scores/{data['scores'][0]}", {"score": 1}),
        ]:
            denied = getattr(client, method)(url, headers=supervisor, json=payload)
            assert denied.status_code == 403, (url, denied.text)
    # 撤销后旧 token 立即失去新增查看权，原有任课关系仍存在。
    assert client.put(f"/api/users/{data['manager']}/supervisor", headers=admin, json={"stage": ""}).status_code == 200
    assert client.get("/api/users/supervision-classes", headers=supervisor).status_code == 403
    assert client.get("/api/monthly-reports/writing-status", headers=supervisor, params=params).status_code == 403
    assert client.get("/api/monthly-exam-scores/overview", headers=supervisor, params={"scope": "supervision"}).status_code == 403
    if index == 0:
        assert client.get(f"/api/monthly-reports/{data['reports'][0]}", headers=supervisor).status_code == 403
    assert db.query(ClassTeacher).filter_by(teacher_id=data["manager"]).count() == 1


def test_only_admin_can_assign_active_subject_teachers(client, auth, db, supervision_data, seed_users):
    data = supervision_data
    url = f"/api/users/{data['manager']}/supervisor"
    assert client.put(url, headers=auth("stage-manager"), json={"stage": "初中"}).status_code == 403
    assert client.get("/api/users/supervisors?stage=初中", headers=auth("stage-regular")).status_code == 403
    admin = auth("admin")
    assert client.put(f"/api/users/{seed_users['teacher1']}/supervisor", headers=admin, json={"stage": "初中"}).status_code == 400
    assert client.put(url, headers=admin, json={"stage": "小学"}).status_code == 422
    db.get(User, data["manager"]).status = "disabled"; db.commit()
    assert client.put(url, headers=admin, json={"stage": "初中"}).status_code == 400
    assert db.query(CaseAuditLog).filter_by(action="user.supervisor_changed").count() == 0


def test_stage_assignment_is_audited_and_not_inferred_from_grade(client, auth, db, supervision_data):
    data = supervision_data
    cls = db.get(Class, data["classes"][1]); cls.grade = "初三"; db.commit()
    admin = auth("admin")
    assert client.put(f"/api/users/{data['manager']}/supervisor", headers=admin, json={"stage": "初中"}).status_code == 200
    rows = client.get("/api/users/supervisors?stage=初中", headers=admin).json()
    assert [row["id"] for row in rows] == [data["manager"]]
    result = client.get("/api/users/supervision-classes", headers=auth("stage-manager")).json()
    assert [c["id"] for c in result] == [data["classes"][0]]
    audit = db.query(CaseAuditLog).filter_by(action="user.supervisor_changed").one()
    assert audit.detail == {"from": "", "to": "初中"}
