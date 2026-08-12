"""阶段6：结构化反馈生成、教师发布、学生可见性和权限隔离。"""

from app.models.feedback import FeedbackReport
from tests.helpers import default_answers, setup_teacher_assignment, submit_text


def _reviewed_submission(client, auth, seed_users):
    aid, qids = setup_teacher_assignment(
        client, auth, seed_users["kp"], student_ids=[seed_users["student1"]]
    )
    sub_id = submit_text(client, auth, aid, default_answers(qids))
    r = client.post(f"/api/submissions/{sub_id}/confirm-all", headers=auth("teacher1"))
    assert r.status_code == 200, r.text
    assignment = client.get(f"/api/assignments/{aid}", headers=auth("teacher1")).json()
    return aid, assignment["class_id"]


def _generate_assignment(client, auth, student_id, assignment_id, class_id):
    return client.post(
        f"/api/students/{student_id}/feedback/generate",
        json={
            "report_type": "assignment",
            "class_id": class_id,
            "assignment_id": assignment_id,
        },
        headers=auth("teacher1"),
    )


def test_assignment_feedback_generate_publish_and_student_view(
    client, auth, seed_users, db
):
    aid, class_id = _reviewed_submission(client, auth, seed_users)
    sid = seed_users["student1"]
    r = _generate_assignment(client, auth, sid, aid, class_id)
    assert r.status_code == 200, r.text
    report = r.json()
    assert report["status"] == "generated"
    assert report["final_content"]
    assert report["input_snapshot"]["student_alias"] == f"student_{sid}"
    assert "student_name" not in report["input_snapshot"]

    # 未发布前学生不可见。
    r = client.get(f"/api/students/{sid}/feedback", headers=auth("student1"))
    assert r.status_code == 200
    assert r.json() == []

    r = client.put(
        f"/api/feedback/{report['id']}",
        json={"final_content": "教师确认后的反馈内容"},
        headers=auth("teacher1"),
    )
    assert r.status_code == 200, r.text
    r = client.post(
        f"/api/feedback/{report['id']}/publish", headers=auth("teacher1")
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "published"

    r = client.get(f"/api/students/{sid}/feedback", headers=auth("student1"))
    assert r.status_code == 200, r.text
    assert len(r.json()) == 1
    assert r.json()[0]["final_content"] == "教师确认后的反馈内容"
    assert db.get(FeedbackReport, report["id"]).reviewed_by == seed_users["teacher1"]


def test_weekly_feedback_and_duplicate_regeneration(client, auth, seed_users):
    aid, class_id = _reviewed_submission(client, auth, seed_users)
    sid = seed_users["student1"]
    payload = {"report_type": "weekly", "class_id": class_id}
    first = client.post(
        f"/api/students/{sid}/feedback/generate",
        json=payload,
        headers=auth("teacher1"),
    )
    assert first.status_code == 200, first.text
    assert first.json()["input_snapshot"]["assignment_count"] == 1
    second = client.post(
        f"/api/students/{sid}/feedback/generate",
        json=payload,
        headers=auth("teacher1"),
    )
    assert second.status_code == 200, second.text
    assert second.json()["id"] == first.json()["id"]


def test_weekly_feedback_without_reviewed_assignment_rejected(client, auth, seed_users):
    aid, _ = setup_teacher_assignment(
        client, auth, seed_users["kp"], student_ids=[seed_users["student1"]]
    )
    assignment = client.get(f"/api/assignments/{aid}", headers=auth("teacher1")).json()
    r = client.post(
        f"/api/students/{seed_users['student1']}/feedback/generate",
        json={"report_type": "weekly", "class_id": assignment["class_id"]},
        headers=auth("teacher1"),
    )
    assert r.status_code == 409


def test_feedback_access_control(client, auth, seed_users):
    aid, class_id = _reviewed_submission(client, auth, seed_users)
    sid = seed_users["student1"]
    report = _generate_assignment(client, auth, sid, aid, class_id).json()

    assert client.post(
        f"/api/students/{sid}/feedback/generate",
        json={"report_type": "assignment", "class_id": class_id, "assignment_id": aid},
        headers=auth("student1"),
    ).status_code == 403
    assert client.get(
        f"/api/students/{sid}/feedback?class_id={class_id}",
        headers=auth("teacher2"),
    ).status_code == 403
    assert client.put(
        f"/api/feedback/{report['id']}",
        json={"final_content": "越权修改"},
        headers=auth("teacher2"),
    ).status_code == 403
    assert client.get(
        f"/api/students/{seed_users['student2']}/feedback",
        headers=auth("student1"),
    ).status_code == 403
