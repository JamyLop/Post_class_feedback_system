"""角色范围回归：德育主任全局可见周测/班级/任务提醒，咨询老师仅见关联学生周测/班级。"""

from datetime import date

from app.core.security import hash_password
from app.models.class_ import Class, ClassStudent, StudentConsultant
from app.models.user import ROLE_CONSULTANT, User


def _setup(client, auth, db, seed_users):
    consultant = User(username="consult1", name="咨询老师", role=ROLE_CONSULTANT,
                      password_hash=hash_password("test123456"))
    db.add(consultant)
    db.flush()
    cls = Class(name="验证班", grade="高三", teacher_id=seed_users["teacher1"])
    db.add(cls)
    db.flush()
    db.add(ClassStudent(class_id=cls.id, student_id=seed_users["student1"]))
    db.add(StudentConsultant(consultant_id=consultant.id, student_id=seed_users["student1"]))
    db.commit()
    for sid in (seed_users["student1"], seed_users["student2"]):
        if db.query(ClassStudent).filter_by(class_id=cls.id, student_id=sid).first() is None:
            db.add(ClassStudent(class_id=cls.id, student_id=sid))
    db.commit()
    for sid, score in ((seed_users["student1"], 80), (seed_users["student2"], 90)):
        r = client.post("/api/weekly-test-scores", headers=auth("teacher1"), json={
            "class_id": cls.id, "student_id": sid, "subject": "数学",
            "exam_date": str(date.today()), "exam_name": "验证周", "score": score, "max_score": 100,
        })
        assert r.status_code == 200, r.text
    return cls


def test_deyu_sees_all_weekly_scores(client, auth, db, seed_users):
    _setup(client, auth, db, seed_users)
    r = client.get("/api/weekly-test-scores", headers=auth("deyu1"))
    assert r.status_code == 200, r.text
    assert len(r.json()) == 2, r.json()


def test_consultant_sees_only_linked_student_scores(client, auth, db, seed_users):
    _setup(client, auth, db, seed_users)
    r = client.get("/api/weekly-test-scores", headers=auth("consult1"))
    assert r.status_code == 200, r.text
    rows = r.json()
    assert len(rows) == 1, rows
    assert rows[0]["student_id"] == seed_users["student1"]
    trend = client.get("/api/weekly-test-scores/trend",
                       headers=auth("consult1"), params={"student_id": seed_users["student1"]})
    assert trend.status_code == 200 and len(trend.json()) == 1
    other = client.get("/api/weekly-test-scores/trend",
                       headers=auth("consult1"), params={"student_id": seed_users["student2"]})
    assert other.status_code == 200 and other.json() == []


def test_deyu_and_admin_can_read_reminders_but_not_checkin(client, auth, db, seed_users):
    _setup(client, auth, db, seed_users)
    for who in ("deyu1", "admin"):
        r = client.get("/api/case-tasks/reminders", headers=auth(who))
        assert r.status_code == 200, (who, r.text)
    r = client.post("/api/case-tasks/batch-checkin",
                    headers=auth("deyu1"), json={"items": []})
    assert r.status_code == 403, r.text


def test_deyu_consultant_class_lists(client, auth, db, seed_users):
    cls = _setup(client, auth, db, seed_users)
    deyu = client.get("/api/classes", headers=auth("deyu1"))
    assert deyu.status_code == 200 and any(c["id"] == cls.id for c in deyu.json())
    consult = client.get("/api/classes", headers=auth("consult1"))
    assert consult.status_code == 200 and any(c["id"] == cls.id for c in consult.json())


def test_storage_files_route_registered(client, auth, db, seed_users):
    routes = [getattr(r, "path", "") for r in client.app.routes]
    assert any(r.startswith("/api/storage/files/") for r in routes), routes
