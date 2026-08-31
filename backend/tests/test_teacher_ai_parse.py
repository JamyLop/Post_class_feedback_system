"""AI 辅助建题（题目解析/批量入库）与教师代提交作业。"""

import json

from tests.helpers import setup_teacher_assignment


def test_parse_text_questions(client, auth, seed_users):
    headers = auth("teacher1")
    r = client.post(
        "/api/questions/parse",
        data={"content_text": "第一题：解方程 x²=4\n\n第二题：计算 3+5"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    questions = r.json()
    assert isinstance(questions, list)
    assert len(questions) == 2
    assert all(q["question_type"] in ("single_choice", "multiple_choice", "judge", "fill", "calculation", "short_answer") for q in questions)
    assert all(q["content"] for q in questions)


def test_parse_empty_input_rejected(client, auth, seed_users):
    headers = auth("teacher1")
    r = client.post("/api/questions/parse", data={"content_text": "  "}, headers=headers)
    assert r.status_code == 400
    r = client.post("/api/questions/parse", data={}, headers=headers)
    assert r.status_code == 400


def test_parse_requires_manager_role(client, auth, seed_users):
    # 学生无权解析
    r = client.post("/api/questions/parse", data={"content_text": "x=1"}, headers=auth("student1"))
    assert r.status_code in (401, 403)


def test_batch_create_questions(client, auth, seed_users):
    headers = auth("teacher1")
    r = client.post(
        "/api/questions/batch",
        json={
            "questions": [
                {
                    "subject": "数学", "grade": "初二", "question_type": "calculation",
                    "content": "解方程 x²-4=0", "standard_answer": "x=±2",
                    "score": 10, "difficulty": 0.5, "knowledge_points": [],
                },
                {
                    "subject": "数学", "grade": "初二", "question_type": "fill",
                    "content": "填空：___", "standard_answer": "3",
                    "score": 5, "difficulty": 0.3, "knowledge_points": [],
                },
            ]
        },
        headers=headers,
    )
    assert r.status_code == 200, r.text
    created = r.json()
    assert len(created) == 2
    assert created[0]["content"] == "解方程 x²-4=0"
    assert created[1]["question_type"] == "fill"


def test_batch_empty_rejected(client, auth, seed_users):
    r = client.post(
        "/api/questions/batch",
        json={"questions": []},
        headers=auth("teacher1"),
    )
    assert r.status_code == 422


def test_parse_then_batch_import_flow(client, auth, seed_users):
    """解析 → 确认 → 批量入库 → 作业加题 的完整链路。"""
    headers = auth("teacher1")
    parsed = client.post(
        "/api/questions/parse",
        data={"content_text": "题目A\n\n题目B"},
        headers=headers,
    ).json()
    assert len(parsed) == 2

    body = {
        "questions": [
            {
                "subject": "数学", "grade": "初二",
                "question_type": q["question_type"],
                "content": q["content"],
                "standard_answer": q.get("standard_answer", ""),
                "score": q.get("score", 10),
                "difficulty": q.get("difficulty", 0.5),
                "knowledge_points": [],
            }
            for q in parsed
        ]
    }
    created = client.post("/api/questions/batch", json=body, headers=headers).json()
    assert len(created) == 2

    # 加入新作业并发布
    cls_id = client.post(
        "/api/classes",
        json={
            "name": "解析班",
            "education_stage": "初中",
            "grade": "初二",
            "class_type": "全年班",
        },
        headers=headers,
    ).json()["id"]
    client.post(
        f"/api/classes/{cls_id}/students",
        json={"student_ids": [seed_users["student1"]]},
        headers=headers,
    )
    aid = client.post(
        "/api/assignments",
        json={"class_id": cls_id, "title": "解析作业", "subject": "数学"},
        headers=headers,
    ).json()["id"]
    client.post(
        f"/api/assignments/{aid}/questions",
        json={"question_ids": [q["id"] for q in created]},
        headers=headers,
    )
    r = client.post(f"/api/assignments/{aid}/publish", headers=headers)
    assert r.status_code == 200, r.text
    assert len(r.json()["questions"]) == 2


def test_teacher_submit_text_for_student(client, auth, seed_users):
    aid, qids = setup_teacher_assignment(
        client, auth, seed_users["kp"], student_ids=[seed_users["student1"], seed_users["student2"]]
    )
    answers = json.dumps([
        {"question_id": qids[0], "student_answer": "B"},
        {"question_id": qids[1], "student_answer": "AC"},
        {"question_id": qids[2], "student_answer": "正确"},
        {"question_id": qids[3], "student_answer": "0；2"},
        {"question_id": qids[4], "student_answer": "x1=5,x2=-1"},
        {"question_id": qids[5], "student_answer": "配方法推导求根公式"},
    ])
    r = client.post(
        f"/api/assignments/{aid}/teacher-submit",
        data={
            "student_id": str(seed_users["student2"]),
            "content_type": "text",
            "content_text": "作业",
            "answers_json": answers,
        },
        headers=auth("teacher1"),
    )
    assert r.status_code == 200, r.text
    sub = r.json()
    assert sub["student_id"] == seed_users["student2"]
    assert sub["status"] in ("submitted", "processing", "ai_graded")


def test_teacher_submit_student_not_in_class(client, auth, seed_users):
    aid, qids = setup_teacher_assignment(client, auth, seed_users["kp"], student_ids=[seed_users["student1"]])
    r = client.post(
        f"/api/assignments/{aid}/teacher-submit",
        data={
            "student_id": str(seed_users["student3"]),
            "content_type": "text",
            "content_text": "作业",
        },
        headers=auth("teacher1"),
    )
    assert r.status_code == 400


def test_teacher_submit_role_guard(client, auth, seed_users):
    aid, qids = setup_teacher_assignment(client, auth, seed_users["kp"], student_ids=[seed_users["student1"]])
    # 学生不能代提交
    r = client.post(
        f"/api/assignments/{aid}/teacher-submit",
        data={
            "student_id": str(seed_users["student1"]),
            "content_type": "text",
            "content_text": "作业",
        },
        headers=auth("student1"),
    )
    assert r.status_code == 403
    # 非任课教师不能代提交
    r = client.post(
        f"/api/assignments/{aid}/teacher-submit",
        data={
            "student_id": str(seed_users["student1"]),
            "content_type": "text",
            "content_text": "作业",
        },
        headers=auth("teacher2"),
    )
    assert r.status_code == 403


def test_teacher_submit_image_flow(client, auth, seed_users):
    """教师上传学生作业图片：进入 OCR → 批改链路。"""
    aid, qids = setup_teacher_assignment(client, auth, seed_users["kp"], student_ids=[seed_users["student1"]])
    import io

    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    r = client.post(
        f"/api/assignments/{aid}/teacher-submit",
        data={
            "student_id": str(seed_users["student1"]),
            "content_type": "image",
        },
        files={"file": ("homework.png", io.BytesIO(png), "image/png")},
        headers=auth("teacher1"),
    )
    assert r.status_code == 200, r.text
    sub = r.json()
    assert sub["content_type"] == "image"
    assert sub["content_url"]
    assert sub["status"] in ("submitted", "processing", "ai_graded", "failed")


def test_teacher_submit_reviewed_cannot_overwrite(client, auth, seed_users):
    aid, qids = setup_teacher_assignment(client, auth, seed_users["kp"], student_ids=[seed_users["student1"]])
    answers = json.dumps([{"question_id": q, "student_answer": "x"} for q in qids])
    r = client.post(
        f"/api/assignments/{aid}/teacher-submit",
        data={
            "student_id": str(seed_users["student1"]),
            "content_type": "text",
            "content_text": "作业",
            "answers_json": answers,
        },
        headers=auth("teacher1"),
    )
    assert r.status_code == 200, r.text
    sub_id = r.json()["id"]
    # 教师复核完成后，不能再次覆盖
    client.post(f"/api/submissions/{sub_id}/confirm-all", headers=auth("teacher1"))
    r = client.post(
        f"/api/assignments/{aid}/teacher-submit",
        data={
            "student_id": str(seed_users["student1"]),
            "content_type": "text",
            "content_text": "重交",
        },
        headers=auth("teacher1"),
    )
    assert r.status_code == 409
