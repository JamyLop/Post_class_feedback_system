"""Celery 批改任务：JSON 解析失败降级、失败重试、重复任务幂等、唯一约束。"""

import json

import celery.exceptions
import pytest
from sqlalchemy.exc import IntegrityError

from app.models.grading import GradingResult
from app.models.submission import Submission
from app.tasks.grading_tasks import router as gt_router
from app.tasks.grading_tasks import grade_submission
from tests.helpers import SIX_QUESTIONS, default_answers


def _calc_question(kp_id):
    q = next(x for x in SIX_QUESTIONS if x["question_type"] == "calculation")
    q = dict(q)
    q["knowledge_points"] = [{"id": kp_id, "weight": 1.0}]
    return [q]


def _submit(client, auth, aid, answers):
    r = client.post(
        f"/api/assignments/{aid}/submit",
        data={"content_type": "text", "content_text": "作业",
              "answers_json": json.dumps(answers)},
        headers=auth("student1"),
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_parse_failure_falls_back_to_manual(client, auth, seed_users, monkeypatch):
    """LLM 输出非法 JSON：解析失败 → error_type=parse_failed → manual_review。"""
    aid, qids = setup(client, auth, seed_users)

    class BadProvider:
        def chat(self, system, user, response_format="text"):
            return "我不是 JSON"

    monkeypatch.setattr("app.grading.validator.get_llm_provider", lambda: BadProvider())
    # eager 模式：submit 触发批改时即使用坏 provider
    sub_id = _submit(client, auth, aid, [{"question_id": qids[0], "student_answer": "x₁=5, x₂=-1"}])

    grading = client.get(
        f"/api/submissions/{sub_id}/grading", headers=auth("teacher1")
    ).json()
    g = grading["answers"][0]["grading"]
    assert g["error_type"] == "parse_failed"
    assert g["status"] == "manual_review"
    assert g["confidence"] == 0.0
    assert grading["answers"][0]["score"] is None


def test_transient_failure_does_not_mark_failed(client, auth, seed_users, monkeypatch):
    """瞬态失败：任务抛 Retry（触发 Worker 重试），提交状态保持 submitted 而非 failed。

    修复前：第一次异常就置 FAILED，重试因 FAILED 直接跳过，批改永远卡死。
    """
    aid, qids = setup(client, auth, seed_users)

    def boom(params):
        raise RuntimeError("LLM 暂时不可用")

    monkeypatch.setattr(gt_router, "grade", boom)
    with pytest.raises(celery.exceptions.Retry):
        _submit(client, auth, aid, [{"question_id": qids[0], "student_answer": "x₁=5, x₂=-1"}])

    # 关键断言：失败后未进入 failed，重试仍可继续
    sub_id = _last_submission_id(aid)
    assert _get_submission(sub_id).status == "submitted"

    # 修复后（下一次重试成功）→ ai_graded
    monkeypatch.undo()
    grade_submission.apply(args=[sub_id])
    assert _get_submission(sub_id).status == "ai_graded"


def test_retries_exhausted_marks_failed(client, auth, seed_users, monkeypatch, db):
    """重试耗尽：置 failed（此时才允许后续 API 重新触发批改）。"""
    aid, qids = setup(client, auth, seed_users)
    sub_id = _submit(client, auth, aid, [{"question_id": qids[0], "student_answer": "x₁=5, x₂=-1"}])
    # 回到 submitted 状态模拟"首次批改未开始"
    _set_status(sub_id, "submitted")

    def boom(params):
        raise RuntimeError("LLM 彻底不可用")

    monkeypatch.setattr(gt_router, "grade", boom)
    monkeypatch.setattr(grade_submission, "max_retries", 0)  # 首次重试即耗尽
    with pytest.raises(RuntimeError):
        grade_submission.apply(args=[sub_id])
    assert _get_submission(sub_id).status == "failed"

    # 失败后可通过 API 重新触发
    monkeypatch.undo()
    r = client.post(f"/api/submissions/{sub_id}/grade", headers=auth("teacher1"))
    assert r.status_code == 200
    assert _get_submission(sub_id).status == "ai_graded"


def test_duplicate_task_is_idempotent(client, auth, seed_users):
    """同一提交重复触发批改：第二次直接跳过，不重复入账。"""
    aid, qids = setup(client, auth, seed_users, six=True)
    sub_id = _submit(client, auth, aid, default_answers(qids))

    grade_submission.apply(args=[sub_id])  # 第二次触发：status=ai_graded → 跳过
    assert _grading_count(sub_id) == 6


def test_unique_constraint_per_answer(db, client, auth, seed_users):
    """submission_answer_id 唯一约束：重复插入被拒绝。"""
    aid, qids = setup(client, auth, seed_users, six=True)
    sub_id = _submit(client, auth, aid, default_answers(qids))

    grading = client.get(
        f"/api/submissions/{sub_id}/grading", headers=auth("teacher1")
    ).json()
    answer_id = grading["answers"][0]["answer_id"]
    g = db.query(GradingResult).filter(
        GradingResult.submission_answer_id == answer_id
    ).first()

    dup = GradingResult(
        submission_answer_id=answer_id,
        grading_type="rule",
        ai_score=10.0,
        confidence=1.0,
        status="ai_completed",
    )
    db.add(dup)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def setup(client, auth, seed_users, six=False):
    from tests.helpers import setup_teacher_assignment

    questions = None if six else _calc_question(seed_users["kp"])
    return setup_teacher_assignment(
        client, auth, seed_users["kp"], questions=questions,
        student_ids=[seed_users["student1"]],
    )


def _get_submission(submission_id):
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        return db.get(Submission, submission_id)
    finally:
        db.close()


def _set_status(submission_id, status):
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        sub = db.get(Submission, submission_id)
        sub.status = status
        db.commit()
    finally:
        db.close()


def _last_submission_id(assignment_id):
    from app.core.database import SessionLocal
    from app.models.submission import Submission

    db = SessionLocal()
    try:
        return (
            db.query(Submission)
            .filter(Submission.assignment_id == assignment_id)
            .order_by(Submission.id.desc())
            .first()
        ).id
    finally:
        db.close()


def _grading_count(submission_id):
    from app.core.database import SessionLocal
    from app.models.submission import SubmissionAnswer

    db = SessionLocal()
    try:
        return (
            db.query(GradingResult)
            .join(
                SubmissionAnswer,
                SubmissionAnswer.id == GradingResult.submission_answer_id,
            )
            .filter(SubmissionAnswer.submission_id == submission_id)
            .count()
        )
    finally:
        db.close()
