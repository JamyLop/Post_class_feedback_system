"""月考按月份更新、跨月独立、汇总与角色权限回归。"""
from app.models.class_ import Class, ClassStudent
from app.models.weekly_score import WeeklyTestScore


def test_monthly_upsert_summary_trend_and_scope(client, auth, db, seed_users):
    cls = Class(name="月考测试班", grade="高三", teacher_id=seed_users["teacher1"])
    db.add(cls)
    db.flush()
    for name in ("student1", "student2"):
        db.add(ClassStudent(class_id=cls.id, student_id=seed_users[name]))
    db.commit()
    headers = auth("teacher1")
    api = "/api/monthly-exam-scores"
    base = dict(class_id=cls.id, student_id=seed_users["student1"], subject="数学",
                exam_month="2026-09", exam_date="2026-09-05", score=70, max_score=100)
    first = client.post(api, headers=headers, json=base)
    assert first.status_code == 200, first.text
    score_id = first.json()["id"]
    assert first.json()["exam_name"] == "2026-09月考"
    assert client.put(f"{api}/{score_id}/evaluation", headers=headers,
                      json={"content": "加强基础训练"}).status_code == 200
    updated = client.post(api, headers=headers, json={**base, "exam_date": "2026-09-28", "score": 80})
    assert updated.status_code == 200, updated.text
    assert updated.json()["id"] == score_id
    assert updated.json()["evaluations"][0]["content"] == "加强基础训练"
    batch = client.post(api + "/batch", headers=headers, json={
        "class_id": cls.id, "subject": "数学", "exam_month": "2026-09",
        "exam_date": "2026-10-01", "exam_name": "九月月考", "max_score": 100,
        "records": [{"student_id": seed_users["student1"], "score": 90},
                    {"student_id": seed_users["student2"], "score": 70}],
    })
    assert batch.status_code == 200, batch.text
    assert batch.json()[0]["id"] == score_id
    october = client.post(api, headers=headers, json={**base, "exam_month": "2026-10", "exam_date": "2026-10-20", "score": 95})
    assert october.status_code == 200, october.text
    assert october.json()["id"] != score_id
    params = {"class_id": cls.id, "exam_month": "2026-09"}
    rows = client.get(api, headers=headers, params=params).json()
    assert len(rows) == 2
    summary = client.get(api + "/class-summary", headers=headers, params=params).json()
    assert len(summary) == 1
    assert summary[0]["count"] == 2 and summary[0]["avg_score"] == 80
    trend = client.get(api + "/trend", headers=headers, params={"student_id": seed_users["student1"], "subject": "数学"}).json()
    assert [r["exam_month"] for r in trend] == ["2026-09", "2026-10"]
    assert [r["score"] for r in trend] == [90, 95]
    legacy = client.get("/api/weekly-test-scores", headers=headers, params=params)
    assert legacy.status_code == 200 and legacy.json() == rows
    conflict = client.put(f"{api}/{october.json()['id']}", headers=headers, json={"exam_month": "2026-09"})
    assert conflict.status_code == 409
    assert db.query(WeeklyTestScore).count() == 3
    student_headers = auth("student1")
    own = client.get(api, headers=student_headers, params=params).json()
    assert len(own) == 1 and own[0]["student_id"] == seed_users["student1"]
    assert client.post(api, headers=student_headers, json=base).status_code == 403


def test_monthly_batch_validation_is_atomic(client, auth, db, seed_users):
    cls = Class(name="月考校验班", grade="高三", teacher_id=seed_users["teacher1"])
    db.add(cls)
    db.flush()
    db.add(ClassStudent(class_id=cls.id, student_id=seed_users["student1"]))
    db.commit()
    headers = auth("teacher1")
    base = dict(class_id=cls.id, subject="数学", exam_month="2026-09", exam_date="2026-09-30", max_score=100)
    for records in (
        [{"student_id": seed_users["student1"], "score": -1}],
        [{"student_id": seed_users["student1"], "score": 80, "max_score": 0}],
        [{"student_id": seed_users["student1"], "score": 80}] * 2,
    ):
        response = client.post("/api/monthly-exam-scores/batch", headers=headers, json={**base, "records": records})
        assert response.status_code == 422, response.text
    assert db.query(WeeklyTestScore).count() == 0
    response = client.post("/api/monthly-exam-scores/batch", headers=headers,
                           json={**base, "exam_month": "2026-13", "records": [{"student_id": seed_users["student1"], "score": 80}]})
    assert response.status_code == 422


def test_monthly_migration_preserves_history_and_downgrades(db):
    import importlib.util
    from pathlib import Path
    from uuid import uuid4
    from sqlalchemy import text
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    path = Path(__file__).parents[1] / "migrations/versions/c1d2e3f4a5b6_monthly_exam_scores.py"
    spec = importlib.util.spec_from_file_location("monthly_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    # 独立事务和临时 schema 验证真实 PostgreSQL 迁移，最终回滚清理。
    with db.get_bind().connect() as conn:
        tx = conn.begin()
        try:
            schema = "monthly_migration_" + uuid4().hex
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
            conn.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            conn.execute(text("""CREATE TABLE weekly_test_scores (
                id integer PRIMARY KEY, class_id integer, student_id integer,
                subject varchar(32), exam_date date,
                CONSTRAINT uq_weekly_score_student_subject_date
                UNIQUE(class_id, student_id, subject, exam_date))"""))
            conn.execute(text("""INSERT INTO weekly_test_scores VALUES
                (1, 1, 1, '数学', '2026-09-01'),
                (2, 1, 1, '数学', '2026-09-28'),
                (3, 1, 1, '数学', '2026-10-20')"""))
            migration.op = Operations(MigrationContext.configure(conn))
            migration.upgrade()
            rows = conn.execute(text("SELECT id, exam_month FROM weekly_test_scores ORDER BY id")).all()
            assert rows == [(1, None), (2, "2026-09"), (3, "2026-10")]
            migration.downgrade()
            assert conn.execute(text("SELECT count(*) FROM weekly_test_scores")).scalar() == 3
        finally:
            tx.rollback()
