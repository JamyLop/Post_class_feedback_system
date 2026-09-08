"""临时验证3：渠道+咨询关联。"""
from app.models.class_ import StudentConsultant
from app.models.user import User


def test_channel_consultant(client, auth, db, seed_users):
    created = client.post(
        "/api/classes",
        headers=auth("teacher1"),
        json={"name": "高三1班", "education_stage": "高中", "grade": "高三",
              "class_type": "全年班", "school_year": "2026-2027"},
    )
    assert created.status_code == 200, created.text
    class_id = created.json()["id"]

    r = client.get("/api/users?role=consultant", headers=auth("teacher1"))
    assert r.status_code == 200, r.text

    r1 = client.post(
        f"/api/classes/{class_id}/students/create",
        headers=auth("teacher1"),
        json={"name": "新生A", "channel": "转介绍", "enrollment_month": 7, "seat_number": 1},
    )
    assert r1.status_code == 200, r1.text
    assert r1.json()["channel"] == "转介绍"

    r2 = client.post(
        f"/api/classes/{class_id}/students/create",
        headers=auth("teacher1"),
        json={"name": "新生B", "channel": "线上咨询",
              "consultant_id": seed_users["teacher2"],
              "enrollment_month": 7, "seat_number": 2},
    )
    assert r2.status_code == 200, r2.text

    db.expire_all()
    stu = db.query(User).filter_by(username=r2.json()["username"]).one_or_none()
    assert stu is not None
    link = db.query(StudentConsultant).filter_by(
        consultant_id=seed_users["teacher2"], student_id=stu.id).one_or_none()
    assert link is not None

    # 非法咨询老师 → 400，且不影响后续请求（无残留事务）
    r3 = client.post(
        f"/api/classes/{class_id}/students/create",
        headers=auth("teacher1"),
        json={"name": "新生C", "consultant_id": seed_users["student1"],
              "enrollment_month": 7, "seat_number": 3},
    )
    assert r3.status_code == 400, r3.text
    r4 = client.post(
        f"/api/classes/{class_id}/students/create",
        headers=auth("teacher1"),
        json={"name": "新生D", "enrollment_month": 7, "seat_number": 3},
    )
    assert r4.status_code == 200, r4.text
