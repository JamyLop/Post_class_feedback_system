"""手写月度评定的保存、发布、权限和旧 AI 入口回归。"""
import pytest

from app.models.class_ import Class, ClassStudent, StudentGuardian
from app.models.monthly_report import MonthlyReport


@pytest.fixture()
def monthly_setup(db, seed_users):
    cls = Class(name="手写评定测试班", grade="高三", teacher_id=seed_users["teacher1"])
    db.add(cls)
    db.flush()
    db.add_all([
        ClassStudent(class_id=cls.id, student_id=seed_users["student1"]),
        StudentGuardian(parent_id=seed_users["parent1"], student_id=seed_users["student1"]),
    ])
    db.commit()
    return {"student_id": seed_users["student1"], "class_id": cls.id,
            "month_label": "2026-09", "final_content": "  本月学习习惯有进步。\n下月加强错题复盘。  "}


def test_manual_create_edit_publish_visibility(client, auth, db, monthly_setup):
    teacher = auth("teacher1")
    r = client.post("/api/monthly-reports", headers=teacher, json=monthly_setup)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "generated"
    assert data["final_content"] == monthly_setup["final_content"].strip()
    assert data["ai_content"] == "" and data["total_tokens"] == 0
    assert data["input_snapshot"] == {} and data["prompt_version"] == "manual_v1"
    assert data["period_end"] == "2026-09-30"
    url = f"/api/monthly-reports/{data['id']}"
    for role in ("student1", "parent1", "teacher2"):
        assert client.get(url, headers=auth(role)).status_code == 403
    for role in ("student1", "parent1"):
        assert client.get("/api/monthly-reports", headers=auth(role)).json() == []
    assert client.put(url, headers=teacher, json={"final_content": "教师修改后的评定"}).status_code == 200
    assert client.post(url + "/publish", headers=teacher).status_code == 200
    for role in ("student1", "parent1"):
        result = client.get(url, headers=auth(role))
        assert result.status_code == 200
        assert result.json()["final_content"] == "教师修改后的评定"
    duplicate = client.post("/api/monthly-reports", headers=teacher, json=monthly_setup)
    assert duplicate.status_code == 409
    assert client.get(url, headers=teacher).json()["final_content"] == "教师修改后的评定"


@pytest.mark.parametrize("content", ["", "   ", "\n\t", "字" * 8001], ids=["empty", "spaces", "whitespace", "too_long"])
def test_manual_rejects_invalid_content(client, auth, monthly_setup, content):
    assert client.post("/api/monthly-reports", headers=auth("teacher1"),
                       json={**monthly_setup, "final_content": content}).status_code == 422


def test_manual_scope_validation(client, auth, monthly_setup, seed_users):
    for role in ("teacher2", "student1", "parent1"):
        assert client.post("/api/monthly-reports", headers=auth(role), json=monthly_setup).status_code == 403
    for change, status in [({"month_label": "2026-13"}, 400),
                           ({"student_id": seed_users["student2"]}, 403),
                           ({"student_case_id": 999999}, 400)]:
        result = client.post("/api/monthly-reports", headers=auth("teacher1"), json={**monthly_setup, **change})
        assert result.status_code == status, result.text


@pytest.mark.parametrize("legacy_status", ["generating", "failed"])
def test_old_ai_disabled_and_legacy_editable(client, auth, db, monthly_setup, legacy_status):
    from app.tasks.monthly_report_tasks import generate_monthly_report_task
    teacher = auth("teacher1")
    r = client.post("/api/monthly-reports", headers=teacher, json=monthly_setup).json()
    record = db.get(MonthlyReport, r["id"])
    record.status = legacy_status
    record.error_message = "旧生成失败"
    db.commit()
    url = f"/api/monthly-reports/{r['id']}"
    assert client.post("/api/monthly-reports/generate", headers=teacher, json=monthly_setup).status_code == 410
    result = client.put(url, headers=teacher, json={"final_content": "接手手动填写"})
    assert result.status_code == 200 and result.json()["status"] == "generated"
    assert result.json()["error_message"] == ""
    assert client.put(url, headers=teacher, json={"final_content": "  "}).status_code == 422
    assert client.post(url + "/publish", headers=teacher).status_code == 200
    assert generate_monthly_report_task.run(r["id"])["skipped"] is True
    db.expire_all()
    assert db.get(MonthlyReport, r["id"]).final_content == "接手手动填写"
    assert db.get(MonthlyReport, r["id"]).status == "published"


@pytest.mark.parametrize("role,subject", [("head_teacher", "德育"), ("subject_teacher", "数学")])
def test_admin_moves_only_selected_subject(client, auth, db, monthly_setup, seed_users, role, subject):
    from app.models.monthly_report import MonthlyReportEvaluation
    from app.models.student_case import CaseAuditLog
    teacher = auth("teacher1")
    source = client.post("/api/monthly-reports", headers=teacher, json=monthly_setup).json()
    target_data = {**monthly_setup, "month_label": "2026-08", "final_content": "目标月德育"}
    target = client.post("/api/monthly-reports", headers=teacher, json=target_data).json()
    db.add_all([
        MonthlyReportEvaluation(report_id=source["id"], teacher_id=seed_users["teacher2"],
            teacher_name="任课老师", teacher_role="subject_teacher", subject="数学、物理", content="学科内容"),
        MonthlyReportEvaluation(report_id=source["id"], teacher_id=seed_users["teacher1"],
            teacher_name="班主任", teacher_role="head_teacher", subject="", content=source["final_content"]),
    ])
    db.commit()
    url = f"/api/monthly-reports/{source['id']}/month"
    payload = {"month_label": "2026-08", "teacher_role": role, "subject": subject,
               "teacher_id": seed_users["teacher1" if role == "head_teacher" else "teacher2"]}
    for username in ("teacher1", "student1", "parent1"):
        assert client.put(url, headers=auth(username), json=payload).status_code == 403
    admin = auth("admin")
    assert client.put(url, headers=admin, json={"month_label": "2026-08"}).status_code == 422
    if role == "head_teacher":
        assert client.put(url, headers=admin, json=payload).status_code == 409
        payload["month_label"] = "2026-02"
    response = client.put(url, headers=admin, json=payload)
    assert response.status_code == 200, response.text
    moved = response.json()
    db.expire_all()
    original = db.get(MonthlyReport, source["id"])
    assert original.month_label == "2026-09"
    assert original.status == source["status"]
    if role == "head_teacher":
        assert original.final_content == "" and moved["final_content"] == source["final_content"]
        assert moved["period_end"] == "2026-02-28"
        assert original.evaluations[0].subject == "数学、物理"
        assert all(e.teacher_role != "head_teacher" for e in original.evaluations)
        assert moved["evaluations"][0]["teacher_role"] == "head_teacher"
    else:
        assert original.final_content == source["final_content"]
        remaining = next(e for e in original.evaluations if e.teacher_role == "subject_teacher")
        assert remaining.subject == "物理" and remaining.content == "学科内容"
        assert moved["final_content"] == "目标月德育" and moved["status"] == target["status"]
        assert moved["evaluations"][0]["subject"] == "数学"
        assert moved["evaluations"][0]["content"] == "学科内容"
        # 目标月同一教师已有内容时不能再把物理合并过去。
        assert client.put(url, headers=admin, json={**payload, "subject": "物理"}).status_code == 409
        # 只有一个科目时直接移动原评价，保留记录 ID。
        single = client.put(url, headers=admin, json={**payload, "subject": "物理", "month_label": "2026-07"})
        assert single.status_code == 200, single.text
        assert single.json()["evaluations"][0]["id"] == remaining.id
    log = db.query(CaseAuditLog).filter_by(action="monthly_report.month_changed").first()
    assert log.detail["subject"] == subject and log.detail["from_month"] == "2026-09"
    assert client.put(url, headers=admin, json=payload).status_code == 409
