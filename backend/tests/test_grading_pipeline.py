"""六题型批改全链路 + 置信度边界 + 状态流转。"""

from tests.helpers import (
    default_answers,
    setup_teacher_assignment,
    submit_text,
)


def _grading(client, headers, submission_id):
    r = client.get(f"/api/submissions/{submission_id}/grading", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_six_question_types_pipeline(client, auth, seed_users):
    aid, qids = setup_teacher_assignment(client, auth, seed_users["kp"], student_ids=[seed_users["student1"]])
    sub_id = submit_text(client, auth, aid, default_answers(qids))
    # eager 模式下 grade_submission 在提交时同步完成
    grading = _grading(client, auth("teacher1"), sub_id)
    assert grading["status"] == "ai_graded"
    assert len(grading["answers"]) == 6

    by_type = {a["question_type"]: a for a in grading["answers"]}

    # 客观题：规则批改全对
    assert by_type["single_choice"]["score"] == 10
    assert by_type["single_choice"]["grading"]["grading_type"] == "rule"
    assert by_type["single_choice"]["grading"]["confidence"] == 1.0
    assert by_type["multiple_choice"]["score"] == 10
    assert by_type["judge"]["score"] == 10

    # 填空部分错：hybrid 低置信 → 强制人工复核
    fill = by_type["fill"]["grading"]
    assert fill["grading_type"] == "hybrid"
    assert fill["status"] == "manual_review"
    assert fill["confidence"] < 0.70

    # 计算部分对：中置信 → ai_completed（0.70~0.85 提示重点检查）
    calc = by_type["calculation"]["grading"]
    assert calc["grading_type"] == "ai"
    assert calc["status"] == "ai_completed"
    assert 0.70 <= calc["confidence"] < 0.85

    # 简答全对：高置信 → ai_completed
    sa = by_type["short_answer"]["grading"]
    assert sa["status"] == "ai_completed"
    assert sa["confidence"] >= 0.85
    assert by_type["short_answer"]["score"] == 20

    # 总分 = 10+10+10+fill+calc+20
    assert grading["total_score"] == round(
        10 + 10 + 10 + by_type["fill"]["score"] + calc["ai_score"] + 20, 1
    )
    assert grading["max_total"] == 80.0


def test_confidence_high_full_correct(client, auth, seed_users):
    """满分作答：全部高置信，无需人工复核。"""
    aid, qids = setup_teacher_assignment(client, auth, seed_users["kp"], student_ids=[seed_users["student1"]])
    answers = [
        {"question_id": qids[0], "student_answer": "B"},
        {"question_id": qids[1], "student_answer": "AC"},
        {"question_id": qids[2], "student_answer": "对"},
        {"question_id": qids[3], "student_answer": "0；2"},
        {"question_id": qids[4], "student_answer": "x₁=5, x₂=-1"},
        {"question_id": qids[5], "student_answer": "配方法推导求根公式"},
    ]
    sub_id = submit_text(client, auth, aid, answers)
    grading = _grading(client, auth("teacher1"), sub_id)
    assert grading["total_score"] == 80.0
    assert all(
        a["grading"]["status"] == "ai_completed"
        and a["grading"]["confidence"] >= 0.85
        for a in grading["answers"]
    )


def test_confidence_low_all_manual_review(client, auth, seed_users):
    """全部低置信：整份进入人工复核。"""
    aid, qids = setup_teacher_assignment(client, auth, seed_users["kp"], student_ids=[seed_users["student1"]])
    answers = [
        {"question_id": qids[0], "student_answer": "A"},
        {"question_id": qids[1], "student_answer": "B"},
        {"question_id": qids[2], "student_answer": "错"},
        {"question_id": qids[3], "student_answer": "完全不同的答案"},
        {"question_id": qids[4], "student_answer": "乱七八糟"},
        {"question_id": qids[5], "student_answer": "不知道"},
    ]
    sub_id = submit_text(client, auth, aid, answers)
    grading = _grading(client, auth("teacher1"), sub_id)
    assert grading["status"] == "ai_graded"
    fill = next(a for a in grading["answers"] if a["question_type"] == "fill")
    assert fill["grading"]["status"] == "manual_review"
    assert fill["grading"]["confidence"] < 0.70


def test_submission_status_flow(client, auth, seed_users):
    """状态流转：submitted → ai_graded；重复触发批改返回 409。"""
    aid, qids = setup_teacher_assignment(client, auth, seed_users["kp"], student_ids=[seed_users["student1"]])
    sub_id = submit_text(client, auth, aid, default_answers(qids))

    r = client.get(f"/api/submissions/{sub_id}", headers=auth("student1"))
    assert r.status_code == 200
    assert r.json()["status"] == "ai_graded"

    # 已批改后再次触发 → 409
    r = client.post(
        f"/api/submissions/{sub_id}/grade", headers=auth("teacher1")
    )
    assert r.status_code == 409

    # 学生查看自己批改结果 OK
    r = client.get(f"/api/submissions/{sub_id}/grading", headers=auth("student1"))
    assert r.status_code == 200


def test_missing_answer_scored_zero(client, auth, seed_users):
    """未作答：0 分且缺失标记，rule 路径 conf=1.0。"""
    aid, qids = setup_teacher_assignment(client, auth, seed_users["kp"], student_ids=[seed_users["student1"]])
    answers = [
        {"question_id": qids[0], "student_answer": ""},
        {"question_id": qids[1], "student_answer": "AC"},
        {"question_id": qids[2], "student_answer": "对"},
        {"question_id": qids[3], "student_answer": "0；2"},
        {"question_id": qids[4], "student_answer": "x₁=5, x₂=-1"},
        {"question_id": qids[5], "student_answer": "配方法推导求根公式"},
    ]
    sub_id = submit_text(client, auth, aid, answers)
    grading = _grading(client, auth("teacher1"), sub_id)
    sc = next(a for a in grading["answers"] if a["question_type"] == "single_choice")
    assert sc["score"] == 0
    assert sc["grading"]["error_type"] == "missing_answer"
    assert sc["grading"]["confidence"] == 1.0
