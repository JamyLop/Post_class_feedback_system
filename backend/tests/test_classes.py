"""班级学年、编辑与安全删除（新建/编辑/删除由德育主任操作并分配班主任）。"""

from datetime import date

import pytest


def _create_payload(seed_teacher_id, extra=None):
    payload = {
        "name": "高三测试班",
        "education_stage": "高中",
        "grade": "高三",
        "class_type": "全年班",
        "school_year": "2026-2027",
        "school_year_starts_on": "2026-09-01",
        "teacher_id": seed_teacher_id,
    }
    if extra:
        payload.update(extra)
    return payload


def test_class_school_year_edit_and_safe_delete(client, auth, seed_users):
    created = client.post(
        "/api/classes",
        headers=auth("deyu1"),
        json=_create_payload(seed_users["teacher1"]),
    )
    assert created.status_code == 200, created.text
    class_id = created.json()["id"]
    assert created.json()["school_year"] == "2026-2027"
    assert created.json()["school_year_starts_on"] == "2026-09-01"

    updated = client.put(
        f"/api/classes/{class_id}",
        headers=auth("deyu1"),
        json={"name": "高三测试1班", "school_year": "2027-2028", "school_year_starts_on": "2027-08-18"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "高三测试1班"
    assert updated.json()["school_year"] == "2027-2028"
    assert updated.json()["school_year_starts_on"] == "2027-08-18"

    deleted = client.delete(f"/api/classes/{class_id}", headers=auth("deyu1"))
    assert deleted.status_code == 200
    assert deleted.json() == {"ok": True}


def test_teacher_cannot_create_class(client, auth, seed_users):
    """班主任不再直接新建班级，应返回 403；德育主任缺 teacher_id 应 422。"""
    denied = client.post(
        "/api/classes",
        headers=auth("teacher1"),
        json={
            "name": "班主任自建班",
            "education_stage": "高中",
            "grade": "高三",
            "class_type": "全年班",
            "school_year": "2026-2027",
        },
    )
    assert denied.status_code == 403, denied.text
    missing_teacher = client.post(
        "/api/classes",
        headers=auth("deyu1"),
        json={
            "name": "未分配班主任班",
            "education_stage": "高中",
            "grade": "高三",
            "class_type": "全年班",
            "school_year": "2026-2027",
        },
    )
    assert missing_teacher.status_code == 422, missing_teacher.text


def test_class_start_date_defaults_from_school_year(client, auth, seed_users):
    created = client.post(
        "/api/classes",
        headers=auth("deyu1"),
        json={
            "name": "默认开学日班级",
            "education_stage": "高中",
            "grade": "高三",
            "class_type": "全年班",
            "school_year": "2028-2029",
            "teacher_id": seed_users["teacher1"],
        },
    )
    assert created.status_code == 200, created.text
    assert created.json()["school_year_starts_on"] == str(date(2028, 8, 1))


def test_class_category_rules(client, auth, seed_users):
    short_term = client.post(
        "/api/classes",
        headers=auth("deyu1"),
        json={
            "name": "初二暑假班",
            "education_stage": "初中",
            "grade": "初二",
            "class_type": "短期班",
            "short_term_type": "暑假班",
            "school_year": "2026-2027",
            "teacher_id": seed_users["teacher1"],
        },
    )
    assert short_term.status_code == 200, short_term.text
    assert short_term.json()["short_term_type"] == "暑假班"

    junior_training = client.post(
        "/api/classes",
        headers=auth("deyu1"),
        json={
            "name": "初三集训班",
            "education_stage": "初中",
            "grade": "初三",
            "class_type": "集训班",
            "school_year": "2026-2027",
            "teacher_id": seed_users["teacher1"],
        },
    )
    assert junior_training.status_code == 422

    missing_short_term_type = client.post(
        "/api/classes",
        headers=auth("deyu1"),
        json={
            "name": "高一短期班",
            "education_stage": "高中",
            "grade": "高一",
            "class_type": "短期班",
            "school_year": "2026-2027",
            "teacher_id": seed_users["teacher1"],
        },
    )
    assert missing_short_term_type.status_code == 422

    invalid_grade = client.put(
        f"/api/classes/{short_term.json()['id']}",
        headers=auth("deyu1"),
        json={"grade": "高一"},
    )
    assert invalid_grade.status_code == 422


@pytest.mark.parametrize("manager", ["deyu1", "admin"])
def test_rename_only_preserves_class_and_roster(client, auth, seed_users, manager):
    created = client.post("/api/classes", headers=auth("deyu1"), json=_create_payload(seed_users["teacher1"]))
    original = created.json()
    class_id = original["id"]
    enrolled = client.post(
        f"/api/classes/{class_id}/students", headers=auth("deyu1"),
        json={"student_ids": [seed_users["student1"]]},
    )
    assert enrolled.status_code == 200, enrolled.text
    renamed = client.put(
        f"/api/classes/{class_id}", headers=auth(manager), json={"name": "  高三实验1班  "},
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json() == {**original, "name": "高三实验1班"}
    visible = client.get(f"/api/classes/{class_id}", headers=auth("teacher1"))
    assert visible.json()["name"] == "高三实验1班"
    roster = client.get(f"/api/classes/{class_id}/students", headers=auth("deyu1"))
    assert [student["id"] for student in roster.json()] == [seed_users["student1"]]


@pytest.mark.parametrize("username", ["teacher1", "teacher2", "student1", "parent1"])
def test_rename_denies_non_managers(client, auth, seed_users, username):
    created = client.post("/api/classes", headers=auth("deyu1"), json=_create_payload(seed_users["teacher1"]))
    class_id = created.json()["id"]
    denied = client.put(f"/api/classes/{class_id}", headers=auth(username), json={"name": "无权更名"})
    assert denied.status_code == 403, denied.text
    assert client.get(f"/api/classes/{class_id}", headers=auth("deyu1")).json()["name"] == "高三测试班"


@pytest.mark.parametrize("name", ["", " \t\n ", "班" * 65])
def test_rename_rejects_invalid_name(client, auth, seed_users, name):
    created = client.post("/api/classes", headers=auth("deyu1"), json=_create_payload(seed_users["teacher1"]))
    class_id = created.json()["id"]
    rejected = client.put(f"/api/classes/{class_id}", headers=auth("deyu1"), json={"name": name})
    assert rejected.status_code == 422, rejected.text
    assert client.get(f"/api/classes/{class_id}", headers=auth("deyu1")).json()["name"] == "高三测试班"
