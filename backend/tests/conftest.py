"""pytest 全局配置：隔离的 tests schema + Celery eager 模式。

测试使用同一 PostgreSQL 的独立 schema `tests`，与开发库 `public` 隔离。
"""

import os

os.environ["DATABASE_URL"] = (
    "postgresql+psycopg://pfs:pfs@localhost:5432/pfs?options=-csearch_path%3Dtests"
)
os.environ["LLM_PROVIDER"] = "mock"
os.environ["OCR_PROVIDER"] = "mock"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

from app.core.database import Base, SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.tasks.celery_app import celery_app  # noqa: E402

TEST_URL = os.environ["DATABASE_URL"]


@pytest.fixture(scope="session", autouse=True)
def _engine():
    engine = create_engine(TEST_URL)
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS tests"))
        conn.commit()
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(autouse=True)
def _clean_tables(_engine):
    with _engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(text(f'TRUNCATE TABLE "{table.name}" CASCADE'))
    yield


@pytest.fixture()
def client():
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture()
def seed_users(db, _clean_tables):
    """基线账号：admin / teacher1 / teacher2 / student1 / student2 与一个知识点。"""
    from app.core.security import hash_password
    from app.models.knowledge import KnowledgePoint
    from app.models.user import ROLE_ADMIN, ROLE_STUDENT, ROLE_TEACHER, User

    users = [
        ("admin", ROLE_ADMIN, "管理员"),
        ("teacher1", ROLE_TEACHER, "王老师"),
        ("teacher2", ROLE_TEACHER, "李老师"),
        ("student1", ROLE_STUDENT, "张三"),
        ("student2", ROLE_STUDENT, "李四"),
        ("student3", ROLE_STUDENT, "王五"),
    ]
    created = {}
    for username, role, name in users:
        u = User(
            username=username,
            password_hash=hash_password("test123456"),
            name=name,
            role=role,
        )
        db.add(u)
        db.flush()
        created[username] = u.id
    kp = KnowledgePoint(
        subject="数学", grade="初二", chapter="方程与函数",
        name="求根公式", code="test_kp_001",
    )
    db.add(kp)
    db.flush()
    db.commit()
    created["kp"] = kp.id
    return created


def login(client, username, password="test123456"):
    r = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def auth(client, seed_users):
    return lambda username: login(client, username)