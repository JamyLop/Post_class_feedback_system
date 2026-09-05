"""班级学年、编辑与安全删除。"""

from datetime import date

from app.models.assignment import Assignment


def test_class_school_year_edit_and_safe_delete(client, auth, db, seed_users):
    created = client.post(
        "/api/classes",
        headers=auth("teacher1"),
        json={
            "name": "高三测试班",
            "education_stage": "高中",
            "grade": "高三",
            "class_type": "全年班",
            "school_year": "2026-2027",
            "school_year_starts_on": "2026-09-01",
        },
    )
    assert created.status_code == 200, created.text
    class_id = created.json()["id"]
    assert created.json()["school_year"] == "2026-2027"
    assert created.json()["school_year_starts_on"] == "2026-09-01"

    updated = client.put(
        f"/api/classes/{class_id}",
        headers=auth("teacher1"),
        json={"name": "高三测试1班", "school_year": "2027-2028", "school_year_starts_on": "2027-08-18"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "高三测试1班"
    assert updated.json()["school_year"] == "2027-2028"
    assert updated.json()["school_year_starts_on"] == "2027-08-18"

    assignment = Assignment(
        class_id=class_id,
        teacher_id=seed_users["teacher1"],
        title="保留数据测试",
        subject="数学",
        status="draft",
    )
    db.add(assignment)
    db.commit()
    blocked = client.delete(f"/api/classes/{class_id}", headers=auth("teacher1"))
    assert blocked.status_code == 409
    assert "作业" in blocked.json()["detail"]

    db.delete(assignment)
    db.commit()
    deleted = client.delete(f"/api/classes/{class_id}", headers=auth("teacher1"))
    assert deleted.status_code == 200
    assert deleted.json() == {"ok": True}


def test_class_start_date_defaults_from_school_year(client, auth):
    created = client.post(
        "/api/classes",
        headers=auth("teacher1"),
        json={
            "name": "默认开学日班级",
            "education_stage": "高中",
            "grade": "高三",
            "class_type": "全年班",
            "school_year": "2028-2029",
        },
    )
    assert created.status_code == 200, created.text
    assert created.json()["school_year_starts_on"] == str(date(2028, 8, 1))


def test_class_category_rules(client, auth):
    short_term = client.post(
        "/api/classes",
        headers=auth("teacher1"),
        json={
            "name": "初二暑假班",
            "education_stage": "初中",
            "grade": "初二",
            "class_type": "短期班",
            "short_term_type": "暑假班",
            "school_year": "2026-2027",
        },
    )
    assert short_term.status_code == 200, short_term.text
    assert short_term.json()["short_term_type"] == "暑假班"

    junior_training = client.post(
        "/api/classes",
        headers=auth("teacher1"),
        json={
            "name": "初三集训班",
            "education_stage": "初中",
            "grade": "初三",
            "class_type": "集训班",
            "school_year": "2026-2027",
        },
    )
    assert junior_training.status_code == 422

    missing_short_term_type = client.post(
        "/api/classes",
        headers=auth("teacher1"),
        json={
            "name": "高一短期班",
            "education_stage": "高中",
            "grade": "高一",
            "class_type": "短期班",
            "school_year": "2026-2027",
        },
    )
    assert missing_short_term_type.status_code == 422

    invalid_grade = client.put(
        f"/api/classes/{short_term.json()['id']}",
        headers=auth("teacher1"),
        json={"grade": "高一"},
    )
    assert invalid_grade.status_code == 422
