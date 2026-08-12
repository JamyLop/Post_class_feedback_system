"""测试辅助：搭建六题型作业全链路数据。"""

import json

SIX_QUESTIONS = [
    {
        "subject": "数学", "grade": "初二", "question_type": "single_choice",
        "content": "方程 x²-2x-3=0 的解为？", "standard_answer": "B",
        "score": 10, "knowledge_points": [{"id": None, "weight": 1.0}],
    },
    {
        "subject": "数学", "grade": "初二", "question_type": "multiple_choice",
        "content": "下列属于一元二次方程根的是？", "standard_answer": "AC",
        "score": 10, "knowledge_points": [{"id": None, "weight": 1.0}],
    },
    {
        "subject": "数学", "grade": "初二", "question_type": "judge",
        "content": "x=1 是方程 x²-1=0 的根。", "standard_answer": "正确",
        "score": 10, "knowledge_points": [{"id": None, "weight": 1.0}],
    },
    {
        "subject": "数学", "grade": "初二", "question_type": "fill",
        "content": "方程 x²-2x=0 的两个根是：___；___", "standard_answer": "0；2",
        "score": 10, "knowledge_points": [{"id": None, "weight": 1.0}],
    },
    {
        "subject": "数学", "grade": "初二", "question_type": "calculation",
        "content": "用求根公式解方程 x²-4x-5=0。", "standard_answer": "x₁=5, x₂=-1",
        "score": 20, "knowledge_points": [{"id": None, "weight": 1.0}],
    },
    {
        "subject": "数学", "grade": "初二", "question_type": "short_answer",
        "content": "简述一元二次方程求根公式的推导思路。", "standard_answer": "配方法推导求根公式",
        "score": 20, "knowledge_points": [{"id": None, "weight": 1.0}],
    },
]


def bind_kp(questions, kp_id):
    """将动态知识点 id 写入题目定义，返回独立副本。"""
    out = []
    for q in questions:
        q = dict(q)
        q["knowledge_points"] = [{"id": kp_id, "weight": 1.0}]
        out.append(q)
    return out


def setup_teacher_assignment(client, auth, kp_id, questions=None, student_ids=None):
    """教师建班+加学生+建题+建作业+发布，返回 (assignment_id, question_ids)。

    student_ids 缺省时使用 [3]。
    """
    teacher = auth("teacher1")
    r = client.post(
        "/api/classes",
        json={"name": "测试班", "grade": "初二"},
        headers=teacher,
    )
    assert r.status_code == 200, r.text
    cls_id = r.json()["id"]

    r = client.post(
        f"/api/classes/{cls_id}/students",
        json={"student_ids": student_ids or [3]},
        headers=teacher,
    )
    assert r.status_code == 200, r.text

    questions = questions or bind_kp(SIX_QUESTIONS, kp_id)
    qids = []
    for q in questions:
        r = client.post("/api/questions", json=q, headers=teacher)
        assert r.status_code == 200, r.text
        qids.append(r.json()["id"])

    r = client.post(
        "/api/assignments",
        json={"class_id": cls_id, "title": "六题型作业", "subject": "数学"},
        headers=teacher,
    )
    assert r.status_code == 200, r.text
    aid = r.json()["id"]
    r = client.post(
        f"/api/assignments/{aid}/questions",
        json={"question_ids": qids},
        headers=teacher,
    )
    assert r.status_code == 200, r.text
    r = client.post(f"/api/assignments/{aid}/publish", headers=teacher)
    assert r.status_code == 200, r.text
    return aid, qids


def submit_text(client, auth, assignment_id, answers, student="student1"):
    payload = {
        "content_type": "text",
        "content_text": "作业",
        "answers_json": json.dumps(answers),
    }
    r = client.post(
        f"/api/assignments/{assignment_id}/submit",
        data=payload,
        headers=auth(student),
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def default_answers(qids):
    """六题默认答案：客观题全对、填空部分错、计算部分对、简答全对。"""
    return [
        {"question_id": qids[0], "student_answer": "B"},
        {"question_id": qids[1], "student_answer": "A, C"},
        {"question_id": qids[2], "student_answer": "对"},
        {"question_id": qids[3], "student_answer": "3和0"},
        {"question_id": qids[4], "student_answer": "x1=5,x2=-1"},
        {"question_id": qids[5], "student_answer": "配方法推导求根公式"},
    ]
