"""打卡附件上传验收：覆盖小程序快速打卡页调用的完整链路。

链路：创建打卡 → POST multipart(file) 上传照片 → 档案详情自带 url → 单张鉴权读取。
小程序侧用 uni.uploadFile 直调同一接口（见 miniprogram/src/api/studentCases.js）。
"""

import base64
from datetime import date, timedelta

from app.models.class_ import Class, ClassStudent

# 1x1 PNG：满足服务端魔数校验（PNG 签名）的最小合法图片
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _setup(db, seed_users):
    cls = Class(
        name="高三(1)班",
        grade="高三",
        school_year_starts_on=date(2025, 9, 1),
        teacher_id=seed_users["teacher1"],
    )
    db.add(cls)
    db.flush()
    db.add(ClassStudent(class_id=cls.id, student_id=seed_users["student1"]))
    db.commit()
    return cls.id


def _case_and_task(client, auth, class_id, seed_users):
    cycle = client.post(
        "/api/student-cases/cycles",
        headers=auth("admin"),
        json={
            "name": "2026届高三备考周期",
            "school_year": "2025-2026",
            "starts_on": str(date.today() - timedelta(days=30)),
            "ends_on": str(date.today() + timedelta(days=180)),
        },
    )
    assert cycle.status_code == 200, cycle.text
    case = client.post(
        "/api/student-cases",
        headers=auth("teacher1"),
        json={
            "cycle_id": cycle.json()["id"],
            "student_id": seed_users["student1"],
            "class_id": class_id,
            "owner_teacher_id": seed_users["teacher1"],
        },
    )
    assert case.status_code == 200, case.text
    task = client.post(
        f"/api/student-cases/{case.json()['id']}/tasks",
        headers=auth("teacher1"),
        json={
            "subject": "数学",
            "title": "每日限时训练",
            "cadence": "daily",
            "starts_on": str(date.today() - timedelta(days=1)),
            "due_on": str(date.today() + timedelta(days=7)),
            "points": 20,
        },
    )
    assert task.status_code == 200, task.text
    return case.json()["id"], task.json()["id"]


def _checkin(client, auth, task_id):
    r = client.post(
        f"/api/student-cases/tasks/{task_id}/checkins",
        headers=auth("teacher1"),
        json={"completion_rate": 80, "self_check": "基本完成"},
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_checkin_photo_upload_chain(client, auth, db, seed_users):
    class_id = _setup(db, seed_users)
    case_id, task_id = _case_and_task(client, auth, class_id, seed_users)
    checkin_id = _checkin(client, auth, task_id)

    # 1. 班主任上传照片：小程序 uni.uploadFile 同名 file 字段
    up = client.post(
        f"/api/student-cases/task-checkins/{checkin_id}/attachments",
        headers=auth("teacher1"),
        files={"file": ("photo.png", PNG_1X1, "image/png")},
    )
    assert up.status_code == 200, up.text
    assert up.json()["object_name"]
    assert up.json()["url"]

    # 2. 非班主任（学生）上传 → 403
    denied = client.post(
        f"/api/student-cases/task-checkins/{checkin_id}/attachments",
        headers=auth("student1"),
        files={"file": ("photo.png", PNG_1X1, "image/png")},
    )
    assert denied.status_code == 403, denied.text

    # 3. 非图片内容 → 400（魔数校验）
    bad = client.post(
        f"/api/student-cases/task-checkins/{checkin_id}/attachments",
        headers=auth("teacher1"),
        files={"file": ("note.txt", b"hello world", "image/png")},
    )
    assert bad.status_code == 400, bad.text

    # 4. 档案详情自带预签名 url：小程序照片墙依赖此字段
    detail = client.get(f"/api/student-cases/{case_id}", headers=auth("teacher1"))
    assert detail.status_code == 200, detail.text
    checkins = [c for c in detail.json()["task_checkins"] if c["id"] == checkin_id]
    assert len(checkins) == 1
    assert len(checkins[0]["attachments"]) == 1
    assert checkins[0]["attachments"][0]["url"]

    # 5. 单张鉴权读取：小程序直链失败时的 downloadFile 兜底走此接口
    raw = client.get(
        f"/api/student-cases/task-checkins/{checkin_id}/attachments/0",
        headers=auth("teacher1"),
    )
    assert raw.status_code == 200, raw.text
    assert raw.content.startswith(b"\x89PNG")
