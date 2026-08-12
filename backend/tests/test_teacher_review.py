"""阶段4：教师复核 —— 复核队列/单题确认/确认全部/标记异常/知识点记录写入。"""

from tests.helpers import default_answers, setup_teacher_assignment, submit_text
from app.models.knowledge import StudentKnowledgeRecord


def _grading(client, headers, submission_id):
    r = client.get(f"/api/submissions/{submission_id}/grading", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def _pending(client, headers, assignment_id=None):
    url = "/api/reviews"
    if assignment_id:
        url += f"?assignment_id={assignment_id}"
    r = client.get(url, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_review_queue_after_grading(client, auth, seed_users, db):
    aid, qids = setup_teacher_assignment(client, auth, seed_users["kp"], student_ids=[seed_users["student1"]])
    sub_id = submit_text(client, auth, aid, default_answers(qids))

    pending = _pending(client, auth("teacher1"))
    assert len(pending) == 1
    row = pending[0]
    assert row["submission_id"] == sub_id
    assert row["student_name"] == "张三"
    assert row["review_state"] == "pending"
    assert row["confirmed_count"] == 0
    assert row["answer_count"] == 6

    # 已确认队列为空
    confirmed = client.get("/api/reviews?review_status=confirmed", headers=auth("teacher1")).json()
    assert confirmed == []


def test_confirm_single_with_override(client, auth, seed_users, db):
    aid, qids = setup_teacher_assignment(client, auth, seed_users["kp"], student_ids=[seed_users["student1"]])
    sub_id = submit_text(client, auth, aid, default_answers(qids))
    grading = _grading(client, auth("teacher1"), sub_id)

    # 选第一题（客观题，AI 满分）改分数并写评语
    first = grading["answers"][0]
    gid = first["grading"]["id"]
    r = client.put(
        f"/api/gradings/{gid}/confirm",
        json={"teacher_score": 8, "teacher_comment": "过程不完整，扣2分"},
        headers=auth("teacher1"),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    target = next(a for a in body["answers"] if a["answer_id"] == first["answer_id"])
    assert target["grading"]["status"] == "confirmed"
    assert target["grading"]["teacher_score"] == 8
    assert target["grading"]["teacher_comment"] == "过程不完整，扣2分"
    assert target["score"] == 8
    assert target["is_correct"] is False
    assert target["grading"]["reviewed_at"] is not None

    # 知识点记录已写入且正确
    records = (
        db.query(StudentKnowledgeRecord)
        .filter(StudentKnowledgeRecord.assignment_id == aid)
        .all()
    )
    assert len(records) == 1
    rec = records[0]
    assert rec.student_id == seed_users["student1"]
    assert rec.knowledge_point_id == seed_users["kp"]
    assert rec.score == 8
    assert rec.is_correct is False

    # 只确认 1/6 题，submission 仍在待复核
    pending = _pending(client, auth("teacher1"))
    assert pending[0]["confirmed_count"] == 1
    assert pending[0]["review_state"] == "pending"


def test_confirm_all_finalizes_submission(client, auth, seed_users, db):
    aid, qids = setup_teacher_assignment(client, auth, seed_users["kp"], student_ids=[seed_users["student1"]])
    sub_id = submit_text(client, auth, aid, default_answers(qids))

    r = client.post(f"/api/submissions/{sub_id}/confirm-all", headers=auth("teacher1"))
    assert r.status_code == 200, r.text
    body = r.json()
    assert all(a["grading"]["status"] == "confirmed" for a in body["answers"])
    assert body["status"] == "teacher_reviewed"

    records = db.query(StudentKnowledgeRecord).filter(
        StudentKnowledgeRecord.assignment_id == aid
    ).all()
    assert len(records) == 6
    # 用到 AI 分数：empty/缺答客观题 0 分记录 is_correct=False
    assert {rec.question_id for rec in records} == set(qids)

    # 已确认队列出现，待复核消失
    confirmed = client.get("/api/reviews?review_status=confirmed", headers=auth("teacher1")).json()
    assert len(confirmed) == 1
    assert confirmed[0]["confirmed_count"] == 6
    assert confirmed[0]["review_state"] == "confirmed"
    pending = _pending(client, auth("teacher1"))
    assert pending == []


def test_confirm_score_validation(client, auth, seed_users):
    aid, qids = setup_teacher_assignment(client, auth, seed_users["kp"], student_ids=[seed_users["student1"]])
    sub_id = submit_text(client, auth, aid, default_answers(qids))
    grading = _grading(client, auth("teacher1"), sub_id)
    gid = grading["answers"][0]["grading"]["id"]

    r = client.put(
        f"/api/gradings/{gid}/confirm",
        json={"teacher_score": 999},
        headers=auth("teacher1"),
    )
    assert r.status_code == 400


def test_flag_grading_stays_pending(client, auth, seed_users):
    aid, qids = setup_teacher_assignment(client, auth, seed_users["kp"], student_ids=[seed_users["student1"]])
    sub_id = submit_text(client, auth, aid, default_answers(qids))
    grading = _grading(client, auth("teacher1"), sub_id)
    gid = grading["answers"][1]["grading"]["id"]

    r = client.post(f"/api/gradings/{gid}/flag", json={"teacher_comment": "答案识别异常"}, headers=auth("teacher1"))
    assert r.status_code == 200, r.text
    target = next(a for a in r.json()["answers"] if a["grading"]["id"] == gid)
    assert target["grading"]["status"] == "manual_review"
    assert target["grading"]["teacher_comment"].startswith("【标记异常】")

    # 未填写原因 → 400
    r = client.post(f"/api/gradings/{gid}/flag", json={"teacher_comment": "  "}, headers=auth("teacher1"))
    assert r.status_code == 400


def test_confirm_twice_no_duplicate_records(client, auth, seed_users, db):
    aid, qids = setup_teacher_assignment(client, auth, seed_users["kp"], student_ids=[seed_users["student1"]])
    sub_id = submit_text(client, auth, aid, default_answers(qids))
    grading = _grading(client, auth("teacher1"), sub_id)
    gid = grading["answers"][0]["grading"]["id"]

    headers = auth("teacher1")
    client.put(f"/api/gradings/{gid}/confirm", json={"teacher_score": 8}, headers=headers)
    client.put(f"/api/gradings/{gid}/confirm", json={"teacher_score": 6, "teacher_comment": "再扣"}, headers=headers)

    records = db.query(StudentKnowledgeRecord).filter(
        StudentKnowledgeRecord.assignment_id == aid,
        StudentKnowledgeRecord.question_id == qids[0],
    ).all()
    assert len(records) == 1
    assert records[0].score == 6


def test_review_access_control(client, auth, seed_users):
    aid, qids = setup_teacher_assignment(client, auth, seed_users["kp"], student_ids=[seed_users["student1"]])
    sub_id = submit_text(client, auth, aid, default_answers(qids))
    grading = _grading(client, auth("teacher1"), sub_id)
    gid = grading["answers"][0]["grading"]["id"]

    # 其他教师看不到该作业的复核队列
    assert _pending(client, auth("teacher2"), aid) == []
    # 其他教师不能确认
    r = client.put(f"/api/gradings/{gid}/confirm", json={"teacher_score": 8}, headers=auth("teacher2"))
    assert r.status_code == 403
    # 学生无权查看复核队列
    r = client.get("/api/reviews", headers=auth("student1"))
    assert r.status_code in (401, 403)