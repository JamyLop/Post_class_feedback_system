"""阶段5：学情分析 —— 掌握度聚合/学生学情/薄弱点/趋势/单次作业/班级学情。"""

from app.models.grading import GradingResult
from app.models.knowledge import StudentKnowledgeStat
from app.models.submission import SubmissionAnswer

from tests.helpers import default_answers, setup_teacher_assignment, submit_text


def _confirm_all(client, teacher, sub_id):
    r = client.post(f"/api/submissions/{sub_id}/confirm-all", headers=teacher)
    assert r.status_code == 200, r.text
    return r.json()


def _full_pipeline(client, auth, seed_users, student="student1", student_ids=None):
    aid, qids = setup_teacher_assignment(
        client, auth, seed_users["kp"], student_ids=student_ids or [seed_users["student1"]]
    )
    sub_id = submit_text(client, auth, aid, default_answers(qids), student=student)
    _confirm_all(client, auth("teacher1"), sub_id)
    return aid, qids, sub_id


def _assignment_class_id(client, auth, assignment_id):
    r = client.get(f"/api/assignments/{assignment_id}", headers=auth("teacher1"))
    assert r.status_code == 200, r.text
    return r.json()["class_id"]


def _create_assignment_in_class(client, auth, class_id, question_ids):
    teacher = auth("teacher1")
    r = client.post(
        "/api/assignments",
        json={"class_id": class_id, "title": "同班第二次作业", "subject": "数学"},
        headers=teacher,
    )
    assert r.status_code == 200, r.text
    assignment_id = r.json()["id"]
    r = client.post(
        f"/api/assignments/{assignment_id}/questions",
        json={"question_ids": question_ids},
        headers=teacher,
    )
    assert r.status_code == 200, r.text
    r = client.post(f"/api/assignments/{assignment_id}/publish", headers=teacher)
    assert r.status_code == 200, r.text
    return assignment_id


def test_stats_written_on_confirm(client, auth, seed_users, db):
    aid, qids, sub_id = _full_pipeline(client, auth, seed_users)
    stats = (
        db.query(StudentKnowledgeStat)
        .filter(StudentKnowledgeStat.student_id == seed_users["student1"])
        .all()
    )
    assert len(stats) == 1
    stat = stats[0]
    assert stat.knowledge_point_id == seed_users["kp"]
    assert stat.correct_count + stat.wrong_count == 6
    assert 0 < stat.mastery_score < 1


def test_student_knowledge_stats_api(client, auth, seed_users):
    aid, _, _ = _full_pipeline(client, auth, seed_users)
    class_id = _assignment_class_id(client, auth, aid)
    r = client.get(
        f"/api/students/{seed_users['student1']}/knowledge-stats?class_id={class_id}",
        headers=auth("teacher1"),
    )
    assert r.status_code == 200, r.text
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["knowledge_point_id"] == seed_users["kp"]
    assert rows[0]["mastery_score"] > 0
    assert rows[0]["trend"] == "new"


def test_weak_points_top_n(client, auth, seed_users):
    # 第一次作业全对
    aid1, qids1, _ = _full_pipeline(client, auth, seed_users)
    class_id = _assignment_class_id(client, auth, aid1)
    # 同一班级第二次作业全错
    aid2 = _create_assignment_in_class(client, auth, class_id, qids1)
    qids2 = qids1
    wrong = [
        {"question_id": qids2[0], "student_answer": "A"},
        {"question_id": qids2[1], "student_answer": "B"},
        {"question_id": qids2[2], "student_answer": "错"},
        {"question_id": qids2[3], "student_answer": "1和2"},
        {"question_id": qids2[4], "student_answer": "x=0"},
        {"question_id": qids2[5], "student_answer": "不知道"},
    ]
    sub2 = submit_text(client, auth, aid2, wrong)
    _confirm_all(client, auth("teacher1"), sub2)

    r = client.get(
        f"/api/students/{seed_users['student1']}/weak-points?top_n=3&class_id={class_id}",
        headers=auth("teacher1"),
    )
    assert r.status_code == 200, r.text
    weak = r.json()
    assert len(weak) == 1
    assert weak[0]["knowledge_point_id"] == seed_users["kp"]
    # 第一份作业 4 对 2 错 + 第二份全错 6 错 → 4 对 8 错
    assert weak[0]["correct_count"] == 4
    assert weak[0]["wrong_count"] == 8
    assert weak[0]["mastery_score"] == round(4 / 12, 4)
    assert weak[0]["trend"] == "down"


def test_learning_trend_api(client, auth, seed_users):
    aid, _, _ = _full_pipeline(client, auth, seed_users)
    class_id = _assignment_class_id(client, auth, aid)
    r = client.get(
        f"/api/students/{seed_users['student1']}/learning-trend?class_id={class_id}",
        headers=auth("teacher1"),
    )
    assert r.status_code == 200, r.text
    points = r.json()["points"]
    assert len(points) == 1
    assert points[0]["percent"] > 0
    assert points[0]["max_total"] > 0


def test_assignment_analysis(client, auth, seed_users, db):
    aid, qids, sub_id = _full_pipeline(client, auth, seed_users)
    # 部分得分但判错时，题目指标应为答对率 0，而不是得分率 0.5。
    answer = (
        db.query(SubmissionAnswer)
        .filter(
            SubmissionAnswer.submission_id == sub_id,
            SubmissionAnswer.question_id == qids[0],
        )
        .one()
    )
    answer.score = 5
    answer.max_score = 10
    answer.is_correct = False
    db.commit()
    r = client.get(f"/api/assignments/{aid}/analysis", headers=auth("teacher1"))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["submission_count"] == 1
    assert body["average_score"] > 0
    assert body["pass_rate"] in (0.0, 1.0)
    assert sum(body["score_distribution"].values()) == 1
    assert len(body["question_accuracy"]) == 6
    assert len(body["weak_knowledge_points"]) == 1
    assert body["weak_knowledge_points"][0]["knowledge_point_id"] == seed_users["kp"]
    first_question = next(row for row in body["question_accuracy"] if row["question_id"] == qids[0])
    assert first_question["accuracy"] == 0.0


def test_class_analytics(client, auth, seed_users):
    aid, qids, sub_id = _full_pipeline(client, auth, seed_users)
    cls_id = (
        client.get("/api/classes", headers=auth("teacher1")).json()[0]["id"]
    )
    r = client.get(f"/api/classes/{cls_id}/analytics", headers=auth("teacher1"))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["submission_count"] == 1
    assert body["average_score"] > 0
    assert len(body["knowledge_accuracy"]) == 1
    assert len(body["weak_knowledge_points"]) == 1
    assert body["weak_knowledge_points"][0]["mastery_score"] < 1
    # 学生未提交应可查（该生已提交，班级其他学生未提交）
    assert isinstance(body["unsubmitted_students"], list)


def test_class_analytics_isolated_from_other_class(client, auth, seed_users):
    aid1, _, _ = _full_pipeline(client, auth, seed_users)
    aid2, _, _ = _full_pipeline(client, auth, seed_users)
    cls1 = _assignment_class_id(client, auth, aid1)
    cls2 = _assignment_class_id(client, auth, aid2)
    assert cls1 != cls2

    r = client.get(f"/api/classes/{cls1}/analytics", headers=auth("teacher1"))
    assert r.status_code == 200, r.text
    assert r.json()["submission_count"] == 1

    sid = seed_users["student1"]
    r = client.get(
        f"/api/students/{sid}/knowledge-stats?class_id={cls1}",
        headers=auth("teacher1"),
    )
    assert r.status_code == 200, r.text
    assert r.json()[0]["correct_count"] + r.json()[0]["wrong_count"] == 6


def test_unsubmitted_students_use_latest_published_assignment(client, auth, seed_users):
    aid, _ = setup_teacher_assignment(
        client,
        auth,
        seed_users["kp"],
        student_ids=[seed_users["student1"], seed_users["student2"]],
    )
    cls_id = _assignment_class_id(client, auth, aid)
    r = client.get(f"/api/classes/{cls_id}/analytics", headers=auth("teacher1"))
    assert r.status_code == 200, r.text
    assert r.json()["submission_count"] == 0
    assert {row["student_id"] for row in r.json()["unsubmitted_students"]} == {
        seed_users["student1"],
        seed_users["student2"],
    }


def test_student_repeated_errors_api(client, auth, seed_users, db):
    aid, _, sub_id = _full_pipeline(client, auth, seed_users)
    cls_id = _assignment_class_id(client, auth, aid)
    grading_rows = (
        db.query(GradingResult)
        .join(SubmissionAnswer, SubmissionAnswer.id == GradingResult.submission_answer_id)
        .filter(SubmissionAnswer.submission_id == sub_id)
        .limit(2)
        .all()
    )
    assert len(grading_rows) == 2
    for grading in grading_rows:
        grading.error_type = "concept_error"
    db.commit()

    r = client.get(
        f"/api/students/{seed_users['student1']}/repeated-errors?class_id={cls_id}",
        headers=auth("teacher1"),
    )
    assert r.status_code == 200, r.text
    assert {"error_type": "concept_error", "count": 2} in r.json()


def test_analytics_access_control(client, auth, seed_users):
    aid, qids, sub_id = _full_pipeline(client, auth, seed_users)
    sid = seed_users["student1"]
    cls_id = _assignment_class_id(client, auth, aid)

    # 学生可看自己，不可看他人
    r = client.get(f"/api/students/{sid}/knowledge-stats", headers=auth("student1"))
    assert r.status_code == 200
    r = client.get(f"/api/students/{seed_users['student2']}/knowledge-stats", headers=auth("student1"))
    assert r.status_code == 403

    # 其他教师不能看该学生学情 / 作业分析 / 班级学情
    assert client.get(
        f"/api/students/{sid}/knowledge-stats?class_id={cls_id}",
        headers=auth("teacher2"),
    ).status_code == 403
    assert client.get(f"/api/assignments/{aid}/analysis", headers=auth("teacher2")).status_code == 403
    assert client.get(f"/api/classes/{cls_id}/analytics", headers=auth("teacher2")).status_code == 403

    # 匿名 401
    assert client.get(f"/api/students/{sid}/knowledge-stats").status_code in (401, 403)
    # 学生不能看班级/作业分析
    assert client.get(f"/api/assignments/{aid}/analysis", headers=auth("student1")).status_code == 403
    assert client.get(f"/api/classes/{cls_id}/analytics", headers=auth("student1")).status_code == 403
