from datetime import datetime, timedelta, timezone
from pathlib import Path

from tests.helpers import default_answers, setup_teacher_assignment, submit_text


def test_due_assignment_rejects_submission(client, auth, seed_users):
    aid, qids = setup_teacher_assignment(
        client, auth, seed_users["kp"], student_ids=[seed_users["student1"]]
    )
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    updated = client.put(
        f"/api/assignments/{aid}",
        json={"due_at": past},
        headers=auth("teacher1"),
    )
    assert updated.status_code == 200, updated.text
    response = client.post(
        f"/api/assignments/{aid}/submit",
        data={"content_type": "text", "content_text": "作业", "answers_json": "[]"},
        headers=auth("student1"),
    )
    assert response.status_code == 409


def test_reviewed_answer_prevents_submission_overwrite(client, auth, seed_users):
    aid, qids = setup_teacher_assignment(
        client, auth, seed_users["kp"], student_ids=[seed_users["student1"]]
    )
    submission_id = submit_text(client, auth, aid, default_answers(qids))
    grading = client.get(
        f"/api/submissions/{submission_id}/grading", headers=auth("teacher1")
    ).json()
    grading_id = grading["answers"][0]["grading"]["id"]
    confirmed = client.put(
        f"/api/gradings/{grading_id}/confirm",
        json={},
        headers=auth("teacher1"),
    )
    assert confirmed.status_code == 200, confirmed.text

    response = client.post(
        f"/api/assignments/{aid}/submit",
        data={"content_type": "text", "content_text": "重交", "answers_json": "[]"},
        headers=auth("student1"),
    )
    assert response.status_code == 409
    assert client.get(
        f"/api/submissions/{submission_id}", headers=auth("student1")
    ).status_code == 200


def test_uploaded_file_requires_owner_or_assignment_teacher(client, auth, seed_users):
    aid, _ = setup_teacher_assignment(
        client,
        auth,
        seed_users["kp"],
        student_ids=[seed_users["student1"], seed_users["student2"]],
    )
    png = b"\x89PNG\r\n\x1a\n" + b"test-image-content"
    response = client.post(
        f"/api/assignments/{aid}/submit",
        data={"content_type": "image"},
        files={"file": ("answer.png", png, "image/png")},
        headers=auth("student1"),
    )
    assert response.status_code == 200, response.text
    path = response.json()["content_url"]
    try:
        url = f"/api/storage/files/{path}"
        assert client.get(url).status_code == 401
        assert client.get(url, headers=auth("student1")).status_code == 200
        assert client.get(url, headers=auth("student2")).status_code == 403
        assert client.get(url, headers=auth("teacher1")).status_code == 200
        assert client.get(url, headers=auth("teacher2")).status_code == 403
        assert client.get(url, headers=auth("admin")).status_code == 200
    finally:
        stored = Path("local_storage") / path
        if stored.is_file():
            stored.unlink()


def test_upload_rejects_spoofed_file_content(client, auth, seed_users):
    aid, _ = setup_teacher_assignment(
        client, auth, seed_users["kp"], student_ids=[seed_users["student1"]]
    )
    response = client.post(
        f"/api/assignments/{aid}/submit",
        data={"content_type": "pdf"},
        files={"file": ("fake.pdf", b"not a pdf", "application/pdf")},
        headers=auth("student1"),
    )
    assert response.status_code == 400


def test_broker_failure_keeps_submission_and_returns_failed_state(
    client, auth, seed_users, monkeypatch
):
    aid, _ = setup_teacher_assignment(
        client, auth, seed_users["kp"], student_ids=[seed_users["student1"]]
    )

    def broker_down(*args, **kwargs):
        raise ConnectionError("broker unavailable")

    monkeypatch.setattr("app.api.submissions.grade_submission.delay", broker_down)
    response = client.post(
        f"/api/assignments/{aid}/submit",
        data={"content_type": "text", "content_text": "已作答", "answers_json": "[]"},
        headers=auth("student1"),
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "failed"
    submission_id = response.json()["id"]
    persisted = client.get(
        f"/api/submissions/{submission_id}", headers=auth("student1")
    )
    assert persisted.status_code == 200
    assert persisted.json()["status"] == "failed"
