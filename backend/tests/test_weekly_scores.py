"""周测成绩录入必须由录入者明确提供考试满分。"""

from datetime import date

from app.models.class_ import Class, ClassStudent
from app.models.class_ import ClassTeacher, StudentGuardian
from app.models.weekly_score import WeeklyScoreEvaluation
from app.models.user import ROLE_SUBJECT_TEACHER, User
from app.core.security import hash_password
import pytest


def test_weekly_score_requires_recorder_supplied_max_score(client, auth, db, seed_users):
    cls = Class(name="满分录入测试班", grade="高三", teacher_id=seed_users["teacher1"])
    db.add(cls)
    db.flush()
    db.add(ClassStudent(class_id=cls.id, student_id=seed_users["student1"]))
    db.commit()

    payload = {
        "class_id": cls.id,
        "student_id": seed_users["student1"],
        "subject": "语文",
        "exam_date": str(date.today()),
        "exam_name": "满分录入校验",
        "score": 120,
    }
    missing = client.post("/api/weekly-test-scores", headers=auth("teacher1"), json=payload)
    assert missing.status_code == 422

    missing_batch = client.post(
        "/api/weekly-test-scores/batch",
        headers=auth("teacher1"),
        json={
            "class_id": cls.id,
            "subject": "语文",
            "exam_date": str(date.today()),
            "exam_name": "批量满分校验",
            "records": [{"student_id": seed_users["student1"], "score": 120}],
        },
    )
    assert missing_batch.status_code == 422

    created = client.post(
        "/api/weekly-test-scores",
        headers=auth("teacher1"),
        json={**payload, "max_score": 150},
    )
    assert created.status_code == 200, created.text
    assert created.json()["score"] == 120
    assert created.json()["max_score"] == 150


@pytest.fixture()
def evaluation_setup(client, auth, db, seed_users):
    subject = User(username="subject1", name="数学老师", role=ROLE_SUBJECT_TEACHER,
                   password_hash=hash_password("test123456"))
    db.add(subject)
    db.flush()
    cls = Class(name="评价测试班", grade="高三", teacher_id=seed_users["teacher1"])
    other = Class(name="其他班", grade="高三", teacher_id=seed_users["teacher2"])
    db.add_all([cls, other])
    db.flush()
    db.add_all([
        ClassStudent(class_id=cls.id, student_id=seed_users["student1"]),
        ClassStudent(class_id=other.id, student_id=seed_users["student2"]),
        ClassTeacher(class_id=cls.id, teacher_id=subject.id, role="subject_teacher", subject="数学"),
        StudentGuardian(parent_id=seed_users["parent1"], student_id=seed_users["student1"]),
    ])
    db.commit()
    scores = []
    for class_id, student_id, teacher, subject_name in [
        (cls.id, seed_users["student1"], "teacher1", "数学"),
        (cls.id, seed_users["student1"], "teacher1", "英语"),
        (other.id, seed_users["student2"], "teacher2", "数学"),
    ]:
        response = client.post("/api/weekly-test-scores", headers=auth(teacher), json={
            "class_id": class_id, "student_id": student_id, "subject": subject_name,
            "exam_date": "2026-09-05", "exam_name": "第1周", "score": 80, "max_score": 100,
            "remark": "原始备注",
        })
        assert response.status_code == 200, response.text
        scores.append(response.json())
    return scores


def test_independent_evaluations_update_and_student_parent_read(client, auth, db, evaluation_setup, seed_users):
    score = evaluation_setup[0]
    url = f"/api/weekly-test-scores/{score['id']}/evaluation"
    head = client.put(url, headers=auth("teacher1"), json={"content": "  学习习惯有进步  "})
    assert head.status_code == 200, head.text
    assert head.json()["evaluations"][0]["teacher_role"] == "head_teacher"
    assert head.json()["evaluations"][0]["content"] == "学习习惯有进步"
    subject = client.put(url, headers=auth("subject1"), json={"content": "加强函数训练"})
    assert subject.status_code == 200, subject.text
    assert len(subject.json()["evaluations"]) == 2
    assert subject.json()["evaluations"][1]["teacher_role"] == "subject_teacher"
    assert subject.json()["evaluations"][1]["teacher_name"] == "数学老师"
    assert subject.json()["can_evaluate"] is True
    original = subject.json()["evaluations"][1]
    updated = client.put(url, headers=auth("subject1"), json={"content": "加强函数与几何训练"})
    assert updated.status_code == 200, updated.text
    data = updated.json()
    assert len(data["evaluations"]) == 2
    assert data["evaluations"][0]["content"] == "学习习惯有进步"
    assert data["evaluations"][1]["id"] == original["id"]
    assert data["evaluations"][1]["created_at"] == original["created_at"]
    assert data["evaluations"][1]["updated_at"] >= original["updated_at"]
    assert data["recorded_by"] == seed_users["teacher1"]
    assert data["score"] == 80 and data["remark"] == "原始备注"
    for viewer in ("student1", "parent1", "admin"):
        response = client.get("/api/weekly-test-scores", headers=auth(viewer))
        assert response.status_code == 200, response.text
        row = next(r for r in response.json() if r["id"] == score["id"])
        assert len(row["evaluations"]) == 2
        assert row["can_evaluate"] is False
    unrelated = client.get("/api/weekly-test-scores", headers=auth("student3"))
    assert unrelated.json() == []


def test_evaluation_scope_and_identity_cannot_be_forged(client, auth, evaluation_setup):
    own, other_subject, other_class = evaluation_setup
    for user in ("admin", "student1", "parent1", "deyu1", "teacher2"):
        response = client.put(f"/api/weekly-test-scores/{own['id']}/evaluation",
                              headers=auth(user), json={"content": "无权评价"})
        assert response.status_code == 403, (user, response.text)
    for row in (other_subject, other_class):
        response = client.put(f"/api/weekly-test-scores/{row['id']}/evaluation",
                              headers=auth("subject1"), json={"content": "越界评价"})
        assert response.status_code == 403
    for payload in ({"content": " \n "}, {"content": "字" * 2001},
                    {"content": "冒名评价", "teacher_id": 1},
                    {"content": "冒名评价", "teacher_role": "head_teacher"}):
        response = client.put(f"/api/weekly-test-scores/{own['id']}/evaluation",
                              headers=auth("subject1"), json=payload)
        assert response.status_code == 422, response.text
    missing = client.put("/api/weekly-test-scores/999999/evaluation", headers=auth("subject1"), json={"content": "评价"})
    assert missing.status_code == 404


def test_subject_teacher_reads_only_assigned_subject_and_cannot_change_scores(client, auth, evaluation_setup):
    own, other_subject, other_class = evaluation_setup
    headers = auth("subject1")
    response = client.get("/api/weekly-test-scores", headers=headers)
    assert [row["id"] for row in response.json()] == [own["id"]]
    for endpoint, params in [
        ("", {"subject": "英语"}),
        ("", {"class_id": other_class["class_id"]}),
        ("/trend", {"student_id": own["student_id"], "subject": "英语"}),
        ("/trend", {"student_id": other_class["student_id"]}),
        ("/class-summary", {"class_id": own["class_id"], "subject": "英语"}),
        ("/class-summary", {"class_id": other_class["class_id"]}),
    ]:
        response = client.get("/api/weekly-test-scores" + endpoint, headers=headers, params=params)
        assert response.status_code == 200 and response.json() == [], response.text
    assert client.put(f"/api/weekly-test-scores/{own['id']}", headers=headers, json={"score": 99}).status_code == 403
    assert client.delete(f"/api/weekly-test-scores/{own['id']}", headers=headers).status_code == 403


def test_score_changes_keep_evaluations_and_delete_cascades(client, auth, db, evaluation_setup):
    own = evaluation_setup[0]
    headers = auth("teacher1")
    response = client.put(f"/api/weekly-test-scores/{own['id']}/evaluation", headers=headers, json={"content": "继续努力"})
    assert response.status_code == 200
    batch = client.post("/api/weekly-test-scores/batch", headers=headers, json={
        "class_id": own["class_id"], "subject": "数学", "exam_date": "2026-09-05", "max_score": 100,
        "records": [{"student_id": own["student_id"], "score": 85}],
    })
    assert batch.status_code == 200, batch.text
    assert batch.json()[0]["evaluations"][0]["content"] == "继续努力"
    response = client.delete(f"/api/weekly-test-scores/{own['id']}", headers=headers)
    assert response.status_code == 200
    assert db.query(WeeklyScoreEvaluation).filter_by(score_id=own["id"]).count() == 0


def test_class_teacher_relationship_roles_are_respected(client, auth, db, evaluation_setup, seed_users):
    own, english, _ = evaluation_setup
    # 兼容旧 teacher 账号作为学科教师，以及通过关系表指定的班主任。
    relation = ClassTeacher(class_id=own["class_id"], teacher_id=seed_users["teacher2"], role="subject_teacher", subject="数学")
    db.add(relation)
    db.commit()
    headers = auth("teacher2")
    response = client.put(f"/api/weekly-test-scores/{own['id']}/evaluation", headers=headers, json={"content": "数学评价"})
    assert response.status_code == 200
    assert response.json()["evaluations"][0]["teacher_role"] == "subject_teacher"
    assert client.put(f"/api/weekly-test-scores/{english['id']}/evaluation", headers=headers, json={"content": "英语评价"}).status_code == 403
    relation.role = "head_teacher"
    db.commit()
    response = client.put(f"/api/weekly-test-scores/{english['id']}/evaluation", headers=headers, json={"content": "班主任评价"})
    assert response.status_code == 200
    assert response.json()["evaluations"][0]["teacher_role"] == "head_teacher"
