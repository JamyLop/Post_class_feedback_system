"""班级学年、编辑与安全删除。"""

from app.models.assignment import Assignment


def test_class_school_year_edit_and_safe_delete(client, auth, db, seed_users):
    created = client.post(
        "/api/classes",
        headers=auth("teacher1"),
        json={"name": "高三测试班", "grade": "高三", "school_year": "2026-2027"},
    )
    assert created.status_code == 200, created.text
    class_id = created.json()["id"]
    assert created.json()["school_year"] == "2026-2027"

    updated = client.put(
        f"/api/classes/{class_id}",
        headers=auth("teacher1"),
        json={"name": "高三测试1班", "school_year": "2027-2028"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "高三测试1班"
    assert updated.json()["school_year"] == "2027-2028"

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
