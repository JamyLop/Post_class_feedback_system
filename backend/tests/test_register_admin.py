"""注册（邀请码）与管理员控制台接口测试。"""

from datetime import datetime, timedelta, timezone

from app.models.invite import InviteCode


def _create_invite(db, code, role="student", admin_id=None, expires_at=None):
    invite = InviteCode(
        code=code, role=role, created_by=admin_id or 0, expires_at=expires_at
    )
    db.add(invite)
    db.commit()
    return invite.id


def _register(client, username, role="student", code="ABCD1234", password="test123456"):
    return client.post(
        "/api/auth/register",
        json={
            "username": username,
            "password": password,
            "name": "新同学",
            "role": role,
            "invite_code": code,
        },
    )


def test_register_student_with_valid_invite(client, db, seed_users):
    _create_invite(db, "ABCD1234", role="student", admin_id=seed_users["admin"])
    r = _register(client, "newstudent")
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "student"

    invite = db.query(InviteCode).filter(InviteCode.code == "ABCD1234").first()
    assert invite.status == "used"
    assert invite.used_by is not None
    assert invite.used_at is not None


def test_register_teacher_with_valid_invite(client, db, seed_users):
    _create_invite(db, "TEACH0001", role="teacher", admin_id=seed_users["admin"])
    r = _register(client, "newteacher", role="teacher", code="TEACH0001")
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "teacher"


def test_register_rejects_admin_role(client, db, seed_users):
    _create_invite(db, "ADMIN0001", role="teacher", admin_id=seed_users["admin"])
    r = _register(client, "rogue", role="admin", code="ADMIN0001")
    assert r.status_code == 400


def test_register_without_invite(client, db, seed_users):
    r = _register(client, "noinvite", code="NOPE0001")
    assert r.status_code == 400


def test_register_rejects_role_mismatch(client, db, seed_users):
    _create_invite(db, "STU000001", role="student", admin_id=seed_users["admin"])
    r = _register(client, "teacherwannabe", role="teacher", code="STU000001")
    assert r.status_code == 400


def test_register_rejects_used_invite(client, db, seed_users):
    _create_invite(db, "USED0001", role="student", admin_id=seed_users["admin"])
    assert _register(client, "student_a", code="USED0001").status_code == 200
    r = _register(client, "student_b", code="USED0001")
    assert r.status_code == 400


def test_register_rejects_expired_invite(client, db, seed_users):
    _create_invite(
        db, "EXPIRED1", role="student", admin_id=seed_users["admin"],
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    r = _register(client, "latecomer", code="EXPIRED1")
    assert r.status_code == 400


def test_register_rejects_duplicate_username(client, db, seed_users):
    _create_invite(db, "DUP00001", role="student", admin_id=seed_users["admin"])
    assert _register(client, "dupuser", code="DUP00001").status_code == 200
    _create_invite(db, "DUP00002", role="student", admin_id=seed_users["admin"])
    r = _register(client, "dupuser", code="DUP00002")
    assert r.status_code == 409


def test_registered_user_can_login(client, db, seed_users):
    _create_invite(db, "LOGIN001", role="student", admin_id=seed_users["admin"])
    _register(client, "loginuser", code="LOGIN001")
    r = client.post(
        "/api/auth/login",
        json={"username": "loginuser", "password": "test123456"},
    )
    assert r.status_code == 200, r.text


def test_invite_code_requires_admin(client, auth, seed_users):
    r = client.post("/api/admin/invite-codes", json={"role": "student"}, headers=auth("teacher1"))
    assert r.status_code == 403
    r = client.post("/api/admin/invite-codes", json={"role": "student"}, headers=auth("student1"))
    assert r.status_code == 403


def test_admin_creates_and_disables_invite(client, auth, seed_users):
    admin = auth("admin")
    r = client.post("/api/admin/invite-codes", json={"role": "teacher"}, headers=admin)
    assert r.status_code == 200, r.text
    code = r.json()["code"]
    assert len(code) == 8

    list_r = client.get("/api/admin/invite-codes", headers=admin)
    assert list_r.status_code == 200
    assert any(item["code"] == code for item in list_r.json())

    invite_id = r.json()["id"]
    r = client.post(f"/api/admin/invite-codes/{invite_id}/disable", headers=admin)
    assert r.status_code == 200
    # 停用后无法注册
    assert _register(client, "blocked", role="teacher", code=code).status_code == 400


def test_admin_stats(client, auth, seed_users):
    admin = auth("admin")
    r = client.get("/api/admin/stats", headers=admin)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["admin_count"] == 1
    assert data["teacher_count"] == 2
    assert data["student_count"] == 3
    assert data["class_count"] == 0

    assert client.get("/api/admin/stats", headers=auth("teacher1")).status_code == 403
    assert client.get("/api/admin/stats", headers=auth("student1")).status_code == 403
    assert client.get("/api/admin/stats").status_code == 401


def test_admin_delete_user_with_no_data(client, auth, seed_users, db):
    from app.core.security import hash_password
    from app.models.user import User

    db.add(User(username="emptyuser", password_hash=hash_password("x123456"), name="空用户", role="student"))
    db.commit()
    uid = db.query(User).filter(User.username == "emptyuser").first().id

    r = client.delete(f"/api/admin/users/{uid}", headers=auth("admin"))
    assert r.status_code == 200, r.text
    assert db.get(User, uid) is None


def test_admin_cannot_delete_self(client, auth, seed_users):
    r = client.delete(f"/api/admin/users/{seed_users['admin']}", headers=auth("admin"))
    assert r.status_code == 400


def test_admin_cannot_delete_user_with_submissions(client, auth, seed_users):
    from tests.helpers import default_answers, setup_teacher_assignment, submit_text

    aid, qids = setup_teacher_assignment(
        client, auth, seed_users["kp"], student_ids=[seed_users["student1"]]
    )
    submit_text(client, auth, aid, default_answers(qids), student="student1")

    r = client.delete(f"/api/admin/users/{seed_users['student1']}", headers=auth("admin"))
    assert r.status_code == 409
