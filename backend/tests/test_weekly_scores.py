"""周测成绩录入必须由录入者明确提供考试满分。"""

from datetime import date

from app.models.class_ import Class, ClassStudent


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
