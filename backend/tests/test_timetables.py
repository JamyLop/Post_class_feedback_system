"""德育主任排课、教师课表权限与撞课约束。"""

from app.core.security import hash_password
from app.models.class_ import ClassTeacher
from app.models.user import ROLE_SUBJECT_TEACHER, User


def _class_payload(teacher_id: int) -> dict:
    return {
        "name": "高三课表测试班",
        "education_stage": "高中",
        "grade": "高三",
        "class_type": "全年班",
        "school_year": "2026-2027",
        "teacher_id": teacher_id,
    }


def test_deyu_schedules_and_teachers_only_see_their_courses(client, auth, seed_users, db):
    subject_teacher = User(username="subject1", password_hash=hash_password("test123456"), name="数学老师", role=ROLE_SUBJECT_TEACHER, subject="数学")
    db.add(subject_teacher)
    db.commit()
    db.refresh(subject_teacher)

    cls = client.post("/api/classes", headers=auth("deyu1"), json=_class_payload(seed_users["teacher1"]))
    assert cls.status_code == 200, cls.text
    class_id = cls.json()["id"]
    db.add(ClassTeacher(class_id=class_id, teacher_id=subject_teacher.id, role="subject_teacher", subject="数学"))
    db.commit()

    # 德育主任排课时可读取班主任和任课老师名单，但不能获得其他账号列表。
    visible_subjects = client.get("/api/users?role=subject_teacher", headers=auth("deyu1"))
    assert visible_subjects.status_code == 200, visible_subjects.text
    assert [item["id"] for item in visible_subjects.json()] == [subject_teacher.id]

    created = client.post("/api/timetables", headers=auth("deyu1"), json={
        "class_id": class_id, "teacher_id": subject_teacher.id, "subject": "数学", "weekday": 1, "period": 1, "classroom": "201教室",
    })
    assert created.status_code == 200, created.text
    assert created.json()["teacher_name"] == "数学老师"
    assert created.json()["class_name"] == "高三课表测试班"

    mine = client.get("/api/timetables/mine", headers=auth("subject1"))
    assert mine.status_code == 200, mine.text
    assert [(item["subject"], item["class_name"]) for item in mine.json()] == [("数学", "高三课表测试班")]

    # 班主任不能借由查询参数读取任课老师的课程，也不能自行排课。
    other = client.get(f"/api/timetables?teacher_id={subject_teacher.id}", headers=auth("teacher1"))
    assert other.status_code == 200
    assert other.json() == []
    denied = client.post("/api/timetables", headers=auth("teacher1"), json={
        "class_id": class_id, "teacher_id": seed_users["teacher1"], "subject": "班会", "weekday": 2, "period": 1,
    })
    assert denied.status_code == 403


def test_timetable_rejects_unassigned_teacher_and_slot_conflicts(client, auth, seed_users, db):
    cls = client.post("/api/classes", headers=auth("deyu1"), json=_class_payload(seed_users["teacher1"]))
    class_id = cls.json()["id"]
    unassigned = client.post("/api/timetables", headers=auth("deyu1"), json={
        "class_id": class_id, "teacher_id": seed_users["teacher2"], "subject": "班会", "weekday": 1, "period": 1,
    })
    assert unassigned.status_code == 422

    first = client.post("/api/timetables", headers=auth("deyu1"), json={
        "class_id": class_id, "teacher_id": seed_users["teacher1"], "subject": "班会", "weekday": 1, "period": 1,
    })
    assert first.status_code == 200, first.text
    duplicate = client.post("/api/timetables", headers=auth("deyu1"), json={
        "class_id": class_id, "teacher_id": seed_users["teacher1"], "subject": "自习", "weekday": 1, "period": 1,
    })
    assert duplicate.status_code == 409


def test_admin_can_schedule_and_manage_school_timetable(client, auth, seed_users):
    cls = client.post("/api/classes", headers=auth("admin"), json=_class_payload(seed_users["teacher1"]))
    assert cls.status_code == 200, cls.text

    created = client.post("/api/timetables", headers=auth("admin"), json={
        "class_id": cls.json()["id"], "teacher_id": seed_users["teacher1"], "subject": "班会", "weekday": 3, "period": 2,
    })
    assert created.status_code == 200, created.text
    entry_id = created.json()["id"]

    listed = client.get("/api/timetables", headers=auth("admin"))
    assert listed.status_code == 200, listed.text
    assert [item["id"] for item in listed.json()] == [entry_id]

    updated = client.put(f"/api/timetables/{entry_id}", headers=auth("admin"), json={"subject": "主题班会"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["subject"] == "主题班会"

    deleted = client.delete(f"/api/timetables/{entry_id}", headers=auth("admin"))
    assert deleted.status_code == 200, deleted.text


def test_deyu_can_update_period_times_but_teachers_cannot(client, auth, db):
    from app.models.period_time import PeriodTime

    db.add(PeriodTime(period=1, start_time="08:00", end_time="08:45"))
    db.commit()
    updated = client.put(
        "/api/period-times/1",
        headers=auth("deyu1"),
        json={"start_time": "06:30", "end_time": "07:00"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["start_time"] == "06:30"
    denied = client.put(
        "/api/period-times/1",
        headers=auth("teacher1"),
        json={"start_time": "06:30", "end_time": "07:00"},
    )
    assert denied.status_code == 403
