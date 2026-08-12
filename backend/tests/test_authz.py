"""权限边界：学生/教师越权访问与教师资源归属校验。"""

from tests.helpers import default_answers, setup_teacher_assignment, submit_text


def test_cross_teacher_cannot_view_grading(client, auth, seed_users):
    aid, qids = setup_teacher_assignment(client, auth, seed_users["kp"], student_ids=[seed_users["student1"]])
    sub_id = submit_text(client, auth, aid, default_answers(qids), student="student1")

    # teacher2 访问 teacher1 作业的批改详情 → 403
    r = client.get(f"/api/submissions/{sub_id}/grading", headers=auth("teacher2"))
    assert r.status_code == 403

    # teacher1（归属教师）→ 200
    r = client.get(f"/api/submissions/{sub_id}/grading", headers=auth("teacher1"))
    assert r.status_code == 200

    # admin → 200
    r = client.get(f"/api/submissions/{sub_id}/grading", headers=auth("admin"))
    assert r.status_code == 200


def test_cross_teacher_cannot_list_submissions(client, auth, seed_users):
    aid, qids = setup_teacher_assignment(client, auth, seed_users["kp"], student_ids=[seed_users["student1"]])
    submit_text(client, auth, aid, default_answers(qids), student="student1")

    r = client.get(
        f"/api/assignments/{aid}/submissions", headers=auth("teacher2")
    )
    assert r.status_code == 403
    r = client.get(
        f"/api/assignments/{aid}/submissions", headers=auth("teacher1")
    )
    assert r.status_code == 200


def test_cross_teacher_cannot_retry_grading(client, auth, seed_users):
    aid, qids = setup_teacher_assignment(client, auth, seed_users["kp"], student_ids=[seed_users["student1"]])
    sub_id = submit_text(client, auth, aid, default_answers(qids), student="student1")
    grading = client.get(
        f"/api/submissions/{sub_id}/grading", headers=auth("teacher1")
    ).json()
    gid = grading["answers"][0]["grading"]["id"]

    r = client.post(f"/api/gradings/{gid}/retry", headers=auth("teacher2"))
    assert r.status_code == 403


def test_student_cannot_view_others_submission(client, auth, seed_users):
    aid, qids = setup_teacher_assignment(
        client, auth, seed_users["kp"],
        student_ids=[seed_users["student1"], seed_users["student2"]],
    )
    submit_text(client, auth, aid, default_answers(qids), student="student1")

    # 取 student2 的提交
    r = client.post(
        f"/api/assignments/{aid}/submit",
        data={
            "content_type": "text",
            "content_text": "作业",
            "answers_json": '[]',
        },
        headers=auth("student2"),
    )
    assert r.status_code == 200
    sub2 = r.json()["id"]

    # student1 查看 student2 的提交 → 403
    r = client.get(f"/api/submissions/{sub2}", headers=auth("student1"))
    assert r.status_code == 403
    r = client.get(f"/api/submissions/{sub2}/grading", headers=auth("student1"))
    assert r.status_code == 403

    # student2 自己 → 200
    r = client.get(f"/api/submissions/{sub2}", headers=auth("student2"))
    assert r.status_code == 200


def test_student_cannot_trigger_grading(client, auth, seed_users):
    aid, qids = setup_teacher_assignment(client, auth, seed_users["kp"], student_ids=[seed_users["student1"]])
    sub_id = submit_text(client, auth, aid, default_answers(qids), student="student1")

    # 学生触发批改：非教师角色 → 403
    r = client.post(f"/api/submissions/{sub_id}/grade", headers=auth("student2"))
    assert r.status_code == 403


def test_non_member_student_cannot_submit(client, auth, seed_users):
    aid, qids = setup_teacher_assignment(client, auth, seed_users["kp"], student_ids=[seed_users["student1"]])
    # student2 不属于该班级 → 403
    r = client.post(
        f"/api/assignments/{aid}/submit",
        data={"content_type": "text", "content_text": "作业", "answers_json": "[]"},
        headers=auth("student2"),
    )
    assert r.status_code == 403


def test_question_bank_requires_manager_and_detail_serializes(client, auth, seed_users):
    aid, qids = setup_teacher_assignment(
        client, auth, seed_users["kp"], student_ids=[seed_users["student1"]]
    )

    assert client.get("/api/questions").status_code == 401
    assert client.get(f"/api/questions/{qids[0]}").status_code == 401
    detail = client.get(f"/api/questions/{qids[0]}", headers=auth("teacher1"))
    assert detail.status_code == 200, detail.text
    assert detail.json()["knowledge_points"][0]["knowledge_point_id"] == seed_users["kp"]


def test_teacher_cannot_escalate_or_manage_privileged_accounts(client, auth, seed_users):
    teacher = auth("teacher1")
    create_admin = client.post(
        "/api/users",
        json={
            "username": "rogue_admin",
            "password": "test123456",
            "name": "越权管理员",
            "role": "admin",
        },
        headers=teacher,
    )
    assert create_admin.status_code == 403
    assert client.get("/api/users?role=admin", headers=teacher).status_code == 403
    assert client.get(f"/api/users/{seed_users['admin']}", headers=teacher).status_code == 403
    assert client.put(
        f"/api/users/{seed_users['teacher2']}",
        json={"status": "disabled"},
        headers=teacher,
    ).status_code == 403


def test_student_cannot_receive_answers_and_cross_teacher_cannot_read_assignment(
    client, auth, seed_users
):
    aid, _ = setup_teacher_assignment(
        client, auth, seed_users["kp"], student_ids=[seed_users["student1"]]
    )
    student_detail = client.get(f"/api/assignments/{aid}", headers=auth("student1"))
    assert student_detail.status_code == 200
    assert student_detail.json()["questions"]
    assert all(q["standard_answer"] is None for q in student_detail.json()["questions"])

    student_list = client.get("/api/assignments", headers=auth("student1"))
    assert student_list.status_code == 200
    assert all(
        q["standard_answer"] is None
        for assignment in student_list.json()
        for q in assignment["questions"]
    )
    assert client.get(f"/api/assignments/{aid}", headers=auth("teacher2")).status_code == 403
    assert client.get(
        f"/api/assignments/{aid}/questions", headers=auth("teacher2")
    ).status_code == 403
