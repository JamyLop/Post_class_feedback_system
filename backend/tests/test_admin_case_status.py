"""管理员状态维护不影响正式审批边界，执行中允许校级督查。"""
import pytest

from app.models.student_case import CaseAuditLog, CaseReview, CaseVersion, StudentCase
from tests.test_student_cases import _setup_high3, _create_cycle_and_case, _submit_and_approve


def test_admin_review_on_executing_case(client, auth, db, seed_users):
    class_id = _setup_high3(db, seed_users)
    _, case_id = _create_cycle_and_case(client, auth, class_id, seed_users)
    _submit_and_approve(client, auth, case_id)
    payload = {"review_level": "school", "problem": "执行记录需补充", "corrective_action": "本周补齐"}
    url = f"/api/student-cases/{case_id}/reviews"
    response = client.post(url, headers=auth("admin"), json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["review_level"] == "school"
    assert client.post(url, headers=auth("teacher1"), json=payload).status_code == 403
    db.expire_all()
    assert db.get(StudentCase, case_id).status == "executing"


@pytest.mark.parametrize("target", ["draft", "pending_confirmation", "revision_required", "pending_review", "adjusted", "archived"])
def test_admin_status_snapshot_audit_and_concurrency(client, auth, db, seed_users, target):
    class_id = _setup_high3(db, seed_users)
    _, case_id = _create_cycle_and_case(client, auth, class_id, seed_users)
    _submit_and_approve(client, auth, case_id)
    url = f"/api/student-cases/{case_id}/admin-status"
    body = {"expected_status": "executing", "target_status": target, "reason": "核对后调整"}
    assert client.put(url, headers=auth("teacher1"), json=body).status_code == 403
    admin = auth("admin")
    assert client.put(url, headers=admin, json={**body, "reason": "  "}).status_code == 400
    response = client.put(url, headers=admin, json=body)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == target and response.json()["version"] == 1
    assert db.query(CaseVersion).filter_by(student_case_id=case_id).count() == 0
    audit = db.query(CaseAuditLog).filter_by(action="case.admin_status_changed").one()
    assert audit.detail["from"] == "executing" and audit.detail["to"] == target
    assert audit.detail["snapshot"]["case"]["status"] == "executing"
    assert audit.detail["snapshot"]["case"]["overall_problem"] == "数学基础不牢"
    assert client.put(url, headers=admin, json=body).status_code == 409
    if target == "revision_required":
        review = db.query(CaseReview).filter_by(student_case_id=case_id, review_level="school").one()
        assert review.workflow_status == "open" and review.assigned_to == seed_users["teacher1"]
        resubmit = client.post(f"/api/student-cases/{case_id}/transition", headers=auth("teacher1"),
                               json={"target_status": "pending_confirmation", "reason": "已完成整改"})
        assert resubmit.status_code == 200, resubmit.text
        approved = client.post(f"/api/student-cases/{case_id}/deyu-review", headers=auth("deyu1"),
                               json={"decision": "approved", "corrective_action": "审核通过"})
        assert approved.status_code == 200, approved.text
        db.expire_all()
        assert db.get(CaseReview, review.id).workflow_status == "closed"


def test_admin_restore_archived_and_cancel_obsolete_review(client, auth, db, seed_users):
    class_id = _setup_high3(db, seed_users)
    _, case_id = _create_cycle_and_case(client, auth, class_id, seed_users)
    admin = auth("admin")
    url = f"/api/student-cases/{case_id}/admin-status"
    for source, target in [("draft", "revision_required"), ("revision_required", "archived"), ("archived", "draft"), ("draft", "executing")]:
        response = client.put(url, headers=admin, json={"expected_status": source, "target_status": target, "reason": "状态维护"})
        assert response.status_code == 200, response.text
    db.expire_all()
    assert db.query(CaseReview).filter_by(student_case_id=case_id, workflow_status="open").count() == 0
    assert db.query(CaseVersion).filter_by(student_case_id=case_id).count() == 0
    assert db.get(StudentCase, case_id).version == 1
