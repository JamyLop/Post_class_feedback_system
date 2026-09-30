"""咨询老师自主关联及一生一案读写边界。"""
from datetime import date

from app.core.security import hash_password
from app.models.class_ import Class, ClassStudent, StudentConsultant
from app.models.user import ROLE_CONSULTANT, User


def _consultant(db, name):
    user = User(username=name, name=name, role=ROLE_CONSULTANT,
                password_hash=hash_password("test123456"))
    db.add(user)
    db.commit()
    return user


def test_self_link_search_and_idempotency(client, auth, db, seed_users):
    consultant = _consultant(db, "consultant-link")
    other = _consultant(db, "consultant-other")
    sid = seed_users["student1"]
    db.add(StudentConsultant(consultant_id=other.id, student_id=sid))
    db.commit()
    headers = auth(consultant.username)
    assert client.get("/api/users", headers=headers).json() == []
    options = client.get("/api/users/consultant-students", headers=headers,
                         params={"keyword": "student1"}).json()
    assert len(options) == 1 and options[0]["id"] == sid
    assert set(options[0]) == {"id", "name", "username", "linked"}
    assert options[0]["linked"] is False
    for _ in range(2):
        response = client.post("/api/users/consultant-students", headers=headers,
                               json={"student_id": sid})
        assert response.status_code == 200, response.text
        assert response.json()["linked"] is True
    assert db.query(StudentConsultant).filter_by(consultant_id=consultant.id, student_id=sid).count() == 1
    assert db.query(StudentConsultant).filter_by(consultant_id=other.id, student_id=sid).count() == 1
    assert [s["id"] for s in client.get("/api/users", headers=headers).json()] == [sid]
    assert client.post("/api/users/consultant-students", headers=headers,
                       json={"student_id": seed_users["teacher1"]}).status_code == 404
    disabled = db.get(User, seed_users["student2"])
    disabled.status = "disabled"
    db.commit()
    assert client.post("/api/users/consultant-students", headers=headers,
                       json={"student_id": disabled.id}).status_code == 404
    for role in ["student1", "teacher1", "admin", "parent1"]:
        h = auth(role)
        assert client.get("/api/users/consultant-students", headers=h).status_code == 403
        assert client.post("/api/users/consultant-students", headers=h,
                           json={"student_id": sid}).status_code == 403


def test_linked_consultant_can_write_classed_and_classless_cases(client, auth, db, seed_users):
    consultant = _consultant(db, "consultant-writer")
    other = _consultant(db, "consultant-denied")
    headers = auth(consultant.username)
    denied = auth(other.username)
    cls = Class(name="高三测试班", grade="高三", teacher_id=seed_users["teacher1"],
                school_year_starts_on=date(2026, 8, 1))
    db.add(cls)
    db.flush()
    db.add(ClassStudent(class_id=cls.id, student_id=seed_users["student1"]))
    db.commit()
    cycle = client.post("/api/student-cases/cycles", headers=headers, json={
        "name": "2026-2027学年", "school_year": "2026-2027",
        "starts_on": "2026-08-01", "ends_on": "2027-06-30",
    })
    assert cycle.status_code == 200, cycle.text
    for student_name in ["student1", "student2"]:
        sid = seed_users[student_name]
        payload = {"cycle_id": cycle.json()["id"], "student_id": sid,
                   "owner_teacher_id": seed_users["teacher2"]}
        assert client.post("/api/student-cases", headers=denied, json=payload).status_code == 403
        if student_name == "student1":
            # 班主任已建档：自主关联后应复用现有档案，并获得撰写权限。
            created = client.post("/api/student-cases", headers=auth("teacher1"),
                                  json={**payload, "class_id": cls.id,
                                        "owner_teacher_id": seed_users["teacher1"]})
            assert created.status_code == 200, created.text
            assert client.get(f"/api/student-cases/{created.json()['id']}", headers=headers).status_code == 403
        assert client.post("/api/users/consultant-students", headers=headers,
                           json={"student_id": sid}).status_code == 200
        if student_name == "student2":
            created = client.post("/api/student-cases", headers=headers, json=payload)
        assert created.status_code == 200, created.text
        case = created.json()
        assert case["class_id"] == (cls.id if student_name == "student1" else None)
        assert case["owner_teacher_id"] == (seed_users["teacher1"] if student_name == "student1" else consultant.id)
        cid = case["id"]
        detail = client.get(f"/api/student-cases/{cid}", headers=headers)
        assert detail.status_code == 200, detail.text
        assert detail.json()["can_manage"] is True
        edited = client.patch(f"/api/student-cases/{cid}", headers=headers,
                              json={"overall_problem": "咨询老师撰写诊断"})
        assert edited.status_code == 200, edited.text
        assert edited.json()["overall_problem"] == "咨询老师撰写诊断"
        profile = client.put(f"/api/student-cases/{cid}/student-profile", headers=headers,
                             json={"parent_evaluation": "家长反馈"})
        assert profile.status_code == 200, profile.text
        plan = client.put(f"/api/student-cases/{cid}/subject-plans/数学", headers=headers,
                          json={"subject": "数学", "teacher_id": seed_users["teacher2"],
                                "problem_location": "基础薄弱", "struggle_goal": "提高基础题得分"})
        assert plan.status_code == 200, plan.text
        assert plan.json()["problem_location"] == "基础薄弱"
        assert client.get(f"/api/student-cases/{cid}", headers=denied).status_code == 403
        assert client.patch(f"/api/student-cases/{cid}", headers=denied,
                            json={"overall_problem": "越权"}).status_code == 403
        assert client.post("/api/student-cases", headers=headers, json=payload).status_code == 409
