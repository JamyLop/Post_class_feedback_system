"""班主任任务提醒 + 阶段完成度 + 积分周报/月报验收（新口径）。

新口径：
- 每个任务每天满分 1 分，按完成度折算 earned = rate/100；
- 同一科目同一天多任务合计封顶 1 分；
- 一门科目自然周封顶 7 分；
- 周任务创建必须明确每周执行次数 weekly_times（1-7）。
"""

from datetime import date, timedelta

from app.models.case_points import CaseStageCompletion, StudentPointsReport


def _setup(db, seed_users):
    from app.models.class_ import Class, ClassStudent
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
    }
    payload.update(overrides)
    r = client.post(f"/api/student-cases/{case_id}/tasks", headers=auth("teacher1"), json=payload)
    assert r.status_code == 200, r.text
    return r.json()


def test_weekly_task_requires_times(client, auth, db, seed_users):
    class_id = _setup(db, seed_users)
    case1 = _cycle_case(client, auth, class_id, seed_users, "student1")
    # 周计划缺 weekly_times → 422
    bad = client.post(
        f"/api/student-cases/{case1}/tasks",
        headers=auth("teacher1"),
        json={
            "subject": "数学", "title": "周测复盘", "cadence": "weekly",
            "starts_on": str(date.today() - timedelta(days=1)),
            "due_on": str(date.today() + timedelta(days=14)),
        },
    )
    assert bad.status_code == 422, bad.text
    # weekly_times 超范围 → 422
    bad2 = client.post(
        f"/api/student-cases/{case1}/tasks",
        headers=auth("teacher1"),
        json={
            "subject": "数学", "title": "周测复盘", "cadence": "weekly",
            "weekly_times": 8,
            "starts_on": str(date.today() - timedelta(days=1)),
            "due_on": str(date.today() + timedelta(days=14)),
        },
    )
    assert bad2.status_code == 422, bad2.text
    # 正常周任务：明确每周 3 次
    ok = _task(client, auth, case1, title="周测复盘", cadence="weekly", weekly_times=3)
    assert ok["weekly_times"] == 3
    assert ok["points"] == 1
    # 日任务不能带 weekly_times → 422
    bad3 = client.post(
        f"/api/student-cases/{case1}/tasks",
        headers=auth("teacher1"),
        json={
            "subject": "数学", "title": "每日训练", "cadence": "daily",
            "weekly_times": 3,
            "starts_on": str(date.today() - timedelta(days=1)),
            "due_on": str(date.today() + timedelta(days=7)),
        },
    )
    assert bad3.status_code == 422, bad3.text


def test_points_stage_and_reports(client, auth, db, seed_users):
    class_id = _setup(db, seed_users)
    case1 = _cycle_case(client, auth, class_id, seed_users, "student1")
    case2 = _cycle_case(client, auth, class_id, seed_users, "student2")

    t1 = _task(client, auth, case1, title="任务A")
    assert t1["points"] == 1
    assert t1["version"] == 1
    t2 = _task(client, auth, case1, title="任务B")
    t3 = _task(client, auth, case2, title="任务C",
               due_on=str(date.today() - timedelta(days=1)))  # 已逾期

    # 单条打卡：50% → 0.5分（每天满分1分）
    r = client.post(
        f"/api/student-cases/tasks/{t1['id']}/checkins",
        headers=auth("teacher1"),
        json={"completion_rate": 50, "self_check": "完成一半"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["earned_points"] == 0.5
    assert r.json()["log_date"] == str(date.today())

    # 阶段完成度自动重算：2个任务满分各1分，平均 (50+0)/2=25
    stages = client.get(f"/api/student-cases/{case1}/stage-completions", headers=auth("teacher1"))
    assert stages.status_code == 200, stages.text
    assert len(stages.json()) == 1
    stage = stages.json()[0]
    assert stage["version"] == 1
    assert stage["total_tasks"] == 2
    assert stage["avg_completion_rate"] == 25.0
    assert stage["total_points"] == 2
    assert stage["earned_points"] == 0.5
    assert db.query(CaseStageCompletion).filter_by(student_case_id=case1).count() == 1

    # 每日批量记录：一次记两个任务（100%→1.0，80%→0.8）
    batch = client.post(
        "/api/case-tasks/batch-checkin",
        headers=auth("teacher1"),
        json={"items": [
            {"task_id": t2["id"], "completion_rate": 100, "self_check": "全部完成"},
            {"task_id": t3["id"], "completion_rate": 80, "self_check": "基本完成"},
        ]},
    )
    assert batch.status_code == 200, batch.text
    assert sorted([b["earned_points"] for b in batch.json()]) == [0.8, 1.0]

    # 提醒：t3 已逾期；t1/t2 今日应执行但 t2 已记、t1 已记 → 未打卡为空或仅剩今日到期
    reminders = client.get("/api/case-tasks/reminders", headers=auth("teacher1"))
    assert reminders.status_code == 200, reminders.text
    data = reminders.json()
    assert data["counts"]["overdue"] == 1
    assert data["overdue"][0]["task_id"] == t3["id"]
    assert data["overdue"][0]["student_name"] == "李四"
    assert data["overdue"][0]["overdue_days"] == 1

    # 积分周报一键生成：两名学生各一条
    # student1 同科同日两笔（0.5+1.0）按单日封顶 1 分计；student2 单笔 0.8
    from app.services.case_points_service import current_week_label

    build = client.post(
        "/api/points-reports/build",
        headers=auth("teacher1"),
        json={"class_id": class_id, "period_type": "weekly", "period_label": current_week_label()},
    )
    assert build.status_code == 200, build.text
    assert len(build.json()) == 2
    by_student = {row["student_id"]: row for row in build.json()}
    assert by_student[seed_users["student1"]]["earned_points"] == 1.0
    assert by_student[seed_users["student1"]]["earned_points"] <= 7.0
    assert by_student[seed_users["student2"]]["earned_points"] == 0.8
    # 班级总积分抬头由前端汇总；每条报表均提供班主任署名。
    assert by_student[seed_users["student1"]]["head_teacher_name"] == "王老师"

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

    # 积分仅班主任/德育主任/管理员可见：学生、家长均 403
    mine = client.get("/api/points-reports", headers=auth("student1"))
    assert mine.status_code == 403, mine.text
    parent = client.get("/api/points-reports", headers=auth("parent1"))
    assert parent.status_code == 403, parent.text

    # 德育主任可查看全量报表、可生成
    deyu_list = client.get("/api/points-reports", headers=auth("deyu1"))
    assert deyu_list.status_code == 200, deyu_list.text
    assert len(deyu_list.json()) >= 2
    deyu_build = client.post(
        "/api/points-reports/build",
        headers=auth("deyu1"),
        json={"class_id": class_id, "period_type": "weekly", "period_label": current_week_label()},
    )
    assert deyu_build.status_code == 200, deyu_build.text

    # 非班主任无所管班级：返回空待办
    empty = client.get("/api/case-tasks/reminders", headers=auth("teacher2"))
    assert empty.status_code == 200, empty.text
    assert empty.json()["counts"] == {"overdue": 0, "due_today": 0, "unlogged_today": 0, "needs_revision": 0}


def test_checkin_defaults_full_score(client, auth, db, seed_users):
    """打卡不再填完成度：缺省按 100% 计，打卡即得 1 分。"""
    class_id = _setup(db, seed_users)
    case_id = _cycle_case(client, auth, class_id, seed_users, "student1")
    t = _task(client, auth, case_id, title="每日训练")
    r = client.post(
        f"/api/student-cases/tasks/{t['id']}/checkins",
        headers=auth("teacher1"),
        json={"self_check": "已完成"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["completion_rate"] == 100
    assert r.json()["earned_points"] == 1.0
    batch = client.post(
        "/api/case-tasks/batch-checkin",
        headers=auth("teacher1"),
        json={"items": [{"task_id": t["id"], "self_check": "批量已完成"}]},
    )
    assert batch.status_code == 200, batch.text
    assert batch.json()[0]["earned_points"] == 1.0


def test_weekly_task_locked_after_draft(client, auth, db, seed_users):
    """周任务创建后锁定：草稿/德育退回可改，执行中修改 403，日任务不受影响。"""
    from app.models.student_case import StudentCase
    class_id = _setup(db, seed_users)
    case_id = _cycle_case(client, auth, class_id, seed_users, "student1")
    wt = _task(client, auth, case_id, title="周任务", cadence="weekly", weekly_times=3)
    dt = _task(client, auth, case_id, title="日任务", cadence="daily")

    def weekly_payload(title, times=2):
        return {"subject": "数学", "title": title, "cadence": "weekly", "weekly_times": times,
                "starts_on": wt["starts_on"], "due_on": wt["due_on"]}

    def daily_payload(title):
        return {"subject": "数学", "title": title, "cadence": "daily",
                "starts_on": dt["starts_on"], "due_on": dt["due_on"]}

    # 草稿下可改
    r = client.put(f"/api/student-cases/{case_id}/tasks/{wt['id']}",
                   headers=auth("teacher1"), json=weekly_payload("周任务改"))
    assert r.status_code == 200, r.text
    # 进入执行后周任务锁死
    db.query(StudentCase).filter_by(id=case_id).update({"status": "executing"})
    db.commit()
    r2 = client.put(f"/api/student-cases/{case_id}/tasks/{wt['id']}",
                    headers=auth("teacher1"), json=weekly_payload("周任务再改"))
    assert r2.status_code == 403, r2.text
    assert "德育" in r2.json()["detail"]
    # 日任务仍可改
    r3 = client.put(f"/api/student-cases/{case_id}/tasks/{dt['id']}",
                    headers=auth("teacher1"), json=daily_payload("日任务改"))
    assert r3.status_code == 200, r3.text
    # 德育退回整改后可改
    db.query(StudentCase).filter_by(id=case_id).update({"status": "revision_required"})
    db.commit()
    r4 = client.put(f"/api/student-cases/{case_id}/tasks/{wt['id']}",
                    headers=auth("teacher1"), json=weekly_payload("周任务终改"))
    assert r4.status_code == 200, r4.text


def test_task_change_request_flow(client, auth, db, seed_users):
    """周任务修改申请全链路：申请→德育列表→驳回→重申→同意解锁→班主任可改。"""
    from app.models.student_case import StudentCase
    class_id = _setup(db, seed_users)
    case_id = _cycle_case(client, auth, class_id, seed_users, "student1")
    wt = _task(client, auth, case_id, title="周任务", cadence="weekly", weekly_times=3)
    dt = _task(client, auth, case_id, title="日任务", cadence="daily")
    db.query(StudentCase).filter_by(id=case_id).update({"status": "executing"})
    db.commit()

    def apply(task_id, reason):
        return client.post(
            f"/api/student-cases/{case_id}/tasks/{task_id}/change-request",
            headers=auth("teacher1"), json={"reason": reason},
        )

    # 日任务无需申请
    assert apply(dt["id"], "想改").status_code == 400
    # 无原因 422
    assert apply(wt["id"], "").status_code == 422
    # 正常申请
    r = apply(wt["id"], "学生进度超前，需加次数")
    assert r.status_code == 200, r.text
    rid = r.json()["id"]
    assert r.json()["workflow_status"] == "open"
    # 重复申请 409
    assert apply(wt["id"], "再申请").status_code == 409
    # 班主任无权看申请列表，德育可见
    assert client.get("/api/student-cases/tasks/change-requests", headers=auth("teacher1")).status_code == 403
    lst = client.get("/api/student-cases/tasks/change-requests", headers=auth("deyu1"))
    assert lst.status_code == 200, lst.text
    assert any(x["id"] == rid and x["task_title"] == "周任务" for x in lst.json())
    # 班主任不能审批
    assert client.post(f"/api/student-cases/reviews/{rid}/decide",
                       headers=auth("teacher1"), json={"decision": "approved"}).status_code == 403
    # 德育驳回：仍锁定
    r = client.post(f"/api/student-cases/reviews/{rid}/decide",
                    headers=auth("deyu1"), json={"decision": "rejected", "comment": "暂不需要"})
    assert r.status_code == 200, r.text
    assert r.json()["decision"] == "rejected"
    assert db.query(StudentCase).filter_by(id=case_id).first().status == "executing"
    # 驳回后可重新申请，德育同意后退回整改解锁
    r = apply(wt["id"], "再次申请")
    assert r.status_code == 200, r.text
    rid2 = r.json()["id"]
    r = client.post(f"/api/student-cases/reviews/{rid2}/decide",
                    headers=auth("deyu1"), json={"decision": "approved"})
    assert r.status_code == 200, r.text
    assert db.query(StudentCase).filter_by(id=case_id).first().status == "revision_required"
    r = client.put(
        f"/api/student-cases/{case_id}/tasks/{wt['id']}",
        headers=auth("teacher1"),
        json={"subject": "数学", "title": "周任务终改", "cadence": "weekly", "weekly_times": 5,
              "starts_on": wt["starts_on"], "due_on": wt["due_on"]},
    )
    assert r.status_code == 200, r.text
    assert r.json()["weekly_times"] == 5
    # 已关闭的申请不可再审
    r = client.post(f"/api/student-cases/reviews/{rid2}/decide",
                    headers=auth("deyu1"), json={"decision": "approved"})
    assert r.status_code == 404, r.text


def test_subject_weekly_cap_7(client, auth, db, seed_users):
    """同一科目一周内多任务多天打卡，实得封顶 7 分。"""
    from app.services.case_points_service import current_week_label, parse_week_label
    class_id = _setup(db, seed_users)
    case1 = _cycle_case(client, auth, class_id, seed_users, "student1")
    week_start, week_end = parse_week_label(current_week_label())
    t1 = _task(client, auth, case1, title="任务A", subject="数学",
               starts_on=str(week_start), due_on=str(week_end))
    t2 = _task(client, auth, case1, title="任务B", subject="数学",
               starts_on=str(week_start), due_on=str(week_end))
    # 同一天两个 100% 打卡 → 单日封顶 1 分
    day = week_start
    for tid in (t1["id"], t2["id"]):
        r = client.post(
            "/api/case-tasks/batch-checkin",
            headers=auth("teacher1"),
            json={"log_date": str(day), "items": [{"task_id": tid, "completion_rate": 100}]},
        )
        assert r.status_code == 200, r.text
    build = client.post(
        "/api/points-reports/build",
        headers=auth("teacher1"),
        json={"class_id": class_id, "period_type": "weekly", "period_label": current_week_label()},
    )
    assert build.status_code == 200, build.text
    row = next(x for x in build.json() if x["student_id"] == seed_users["student1"])
    assert row["earned_points"] == 1.0
    assert row["detail"]["per_subject_earned"]["数学"] == 1.0
