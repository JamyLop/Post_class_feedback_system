"""Grading API：单题重批的置信度规则、重批状态、改分边界校验（阶段 4 前置）。"""

from tests.helpers import setup_teacher_assignment


def test_regrade_keeps_manual_review_for_low_confidence(client, auth, seed_users):
    """填空部分错（conf<0.70）重批后仍保持 manual_review。"""
    aid, qids = setup_teacher_assignment(client, auth, seed_users["kp"], student_ids=[seed_users["student1"]])
    answers = [
        {"question_id": qids[3], "student_answer": "3和0"},  # fill 低置信
        {"question_id": qids[0], "student_answer": "B"},
        {"question_id": qids[1], "student_answer": "AC"},
        {"question_id": qids[2], "student_answer": "对"},
        {"question_id": qids[4], "student_answer": "x₁=5, x₂=-1"},
        {"question_id": qids[5], "student_answer": "配方法推导求根公式"},
    ]
    sub_id = _submit(client, auth, aid, answers)

    grading = client.get(
        f"/api/submissions/{sub_id}/grading", headers=auth("teacher1")
    ).json()
    fill = next(a for a in grading["answers"] if a["question_type"] == "fill")
    assert fill["grading"]["status"] == "manual_review"
    gid = fill["grading"]["id"]

    r = client.post(f"/api/gradings/{gid}/retry", headers=auth("teacher1"))
    assert r.status_code == 200
    regraded = next(
        a for a in r.json()["answers"] if a["question_type"] == "fill"
    )
    assert regraded["grading"]["status"] == "manual_review"


def test_regrade_high_confidence_stays_ai_completed(client, auth, seed_users):
    """计算题部分对（conf 0.70~0.85）重批后仍为 ai_completed。"""
    aid, qids = setup_teacher_assignment(client, auth, seed_users["kp"], student_ids=[seed_users["student1"]])
    answers = [
        {"question_id": qids[4], "student_answer": "x1=5,x2=-1"},
        {"question_id": qids[0], "student_answer": "B"},
        {"question_id": qids[1], "student_answer": "AC"},
        {"question_id": qids[2], "student_answer": "对"},
        {"question_id": qids[3], "student_answer": "0；2"},
        {"question_id": qids[5], "student_answer": "配方法推导求根公式"},
    ]
    sub_id = _submit(client, auth, aid, answers)

    grading = client.get(
        f"/api/submissions/{sub_id}/grading", headers=auth("teacher1")
    ).json()
    calc = next(a for a in grading["answers"] if a["question_type"] == "calculation")
    gid = calc["grading"]["id"]

    r = client.post(f"/api/gradings/{gid}/retry", headers=auth("teacher1"))
    assert r.status_code == 200
    regraded = next(
        a for a in r.json()["answers"] if a["question_type"] == "calculation"
    )
    assert regraded["grading"]["status"] == "ai_completed"


def test_regrade_unknown_grading_returns_404(client, auth, seed_users):
    r = client.post("/api/gradings/999999/retry", headers=auth("teacher1"))
    assert r.status_code == 404


def test_grading_not_found(client, auth, seed_users):
    r = client.get("/api/submissions/999999/grading", headers=auth("teacher1"))
    assert r.status_code == 404


def _submit(client, auth, aid, answers):
    import json

    r = client.post(
        f"/api/assignments/{aid}/submit",
        data={"content_type": "text", "content_text": "作业",
              "answers_json": json.dumps(answers)},
        headers=auth("student1"),
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]
