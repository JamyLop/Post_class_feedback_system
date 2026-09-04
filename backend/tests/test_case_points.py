"""班主任任务提醒 + 阶段完成度 + 积分周报/月报验收。"""

from datetime import date, timedelta

from app.models.case_points import CaseStageCompletion, StudentPointsReport
from app.models.class_ import Class, ClassStudent


def _setup(db, seed_users):
    cls = Class(
        name="高三(1)班",
        grade="高三",
        school_year_starts_on=date(2025, 9, 1),
        teacher_id=seed_users["teacher1"],
    )
    db.add(cls)
    db.flush()
    db.add_all([
        ClassStudent(class_id=cls.id, student_id=seed_users["student1"]),
        ClassStudent(class_id=cls.id, student_id=seed_users["student2"]),
    ])
    db.commit()
    return cls.id


def _cycle_case(client, auth, class_id, seed_users, student_key="student1"):
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
            "student_id": seed_users[student_key],
            "class_id": class_id,
            "owner_teacher_id": seed_users["teacher1"],
        },
    )
    assert case.status_code == 200, case.text
    return case.json()["id"]


def _task(client, auth, case_id, **overrides):
    payload = {
        "subject": "数学",
        "title": "每日限时训练",
        "cadence": "daily",
        "starts_on": str(date.today() - timedelta(days=1)),
        "due_on": str(date.today() + timedelta(days=7)),
        "points": 20,
    }
    payload.update(overrides)
    r = client.post(f"/api/student-cases/{case_id}/tasks", headers=auth("teacher1"), json=payload)
    assert r.status_code == 200, r.text
    return r.json()


def test_points_stage_and_reports(client, auth, db, seed_users):
    class_id = _setup(db, seed_users)
    case1 = _cycle_case(client, auth, class_id, seed_users, "student1")
    case2 = _cycle_case(client, auth, class_id, seed_users, "student2")

    t1 = _task(client, auth, case1, title="任务A", points=20)
    assert t1["points"] == 20
    assert t1["version"] == 1
    t2 = _task(client, auth, case1, title="任务B", points=10)
    t3 = _task(client, auth, case2, title="任务C", points=10,
               due_on=str(date.today() - timedelta(days=1)))  # 已逾期

    # 单条打卡：50% → 10分
    r = client.post(
        f"/api/student-cases/tasks/{t1['id']}/checkins",
        headers=auth("teacher1"),
        json={"completion_rate": 50, "self_check": "完成一半"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["earned_points"] == 10.0
    assert r.json()["log_date"] == str(date.today())

    # 阶段完成度自动重算：2个任务，平均 (50+0)/2=25
    stages = client.get(f"/api/student-cases/{case1}/stage-completions", headers=auth("teacher1"))
    assert stages.status_code == 200, stages.text
    assert len(stages.json()) == 1
    stage = stages.json()[0]
    assert stage["version"] == 1
    assert stage["total_tasks"] == 2
    assert stage["avg_completion_rate"] == 25.0
    assert stage["total_points"] == 30
    assert stage["earned_points"] == 10.0
    assert db.query(CaseStageCompletion).filter_by(student_case_id=case1).count() == 1

    # 每日批量记录：一次记两个任务
    batch = client.post(
        "/api/student-cases/tasks/batch-checkin",
        headers=auth("teacher1"),
        json={"items": [
            {"task_id": t2["id"], "completion_rate": 100, "self_check": "全部完成"},
            {"task_id": t3["id"], "completion_rate": 80, "self_check": "基本完成"},
        ]},
    )
    assert batch.status_code == 200, batch.text
    assert sorted([b["earned_points"] for b in batch.json()]) == [8.0, 10.0]

    # 提醒：t3 已逾期；t1/t2 今日应执行但 t2 已记、t1 已记 → 未打卡为空或仅剩今日到期
    reminders = client.get("/api/student-cases/tasks/reminders", headers=auth("teacher1"))
    assert reminders.status_code == 200, reminders.text
    data = reminders.json()
    assert data["counts"]["overdue"] == 1
    assert data["overdue"][0]["task_id"] == t3["id"]
    assert data["overdue"][0]["student_name"] == "李四"
    assert data["overdue"][0]["overdue_days"] == 1

    # 积分周报一键生成：两名学生各一条
    from app.services.case_points_service import current_week_label

    build = client.post(
        "/api/points-reports/build",
        headers=auth("teacher1"),
        json={"class_id": class_id, "period_type": "weekly", "period_label": current_week_label()},
    )
    assert build.status_code == 200, build.text
    assert len(build.json()) == 2
    by_student = {row["student_id"]: row for row in build.json()}
    # student1: 任务A 50%(10分) + 任务B 100%(10分) = 20分
    assert by_student[seed_users["student1"]]["earned_points"] == 20.0
    assert by_student[seed_users["student1"]]["total_points"] == 30.0
    # student2: 任务C 80% → 8分
    assert by_student[seed_users["student2"]]["earned_points"] == 8.0

    # 幂等：重复生成不新增行
    again = client.post(
        "/api/points-reports/build",
        headers=auth("teacher1"),
        json={"class_id": class_id, "period_type": "weekly", "period_label": current_week_label()},
    )
    assert again.status_code == 200, again.text
    assert db.query(StudentPointsReport).filter_by(class_id=class_id).count() == 2

    # 月报
    month = client.post(
        "/api/points-reports/build",
        headers=auth("teacher1"),
        json={"class_id": class_id, "period_type": "monthly"},
    )
    assert month.status_code == 200, month.text
    assert len(month.json()) == 2

    # 学生只能看自己的报表
    mine = client.get("/api/points-reports", headers=auth("student1"))
    assert mine.status_code == 200, mine.text
    assert {row["student_id"] for row in mine.json()} == {seed_users["student1"]}

    # 非班主任无所管班级：返回空待办
    empty = client.get("/api/student-cases/tasks/reminders", headers=auth("teacher2"))
    assert empty.status_code == 200, empty.text
    assert empty.json()["counts"] == {"overdue": 0, "due_today": 0, "unlogged_today": 0}
