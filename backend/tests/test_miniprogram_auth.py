"""认证回归：可用 unittest 单独运行，不连接开发或生产数据库。"""

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.router import router
from app.core.config import settings
from app.core.database import get_db
from app.core.security import ALGORITHM, hash_password


class MiniprogramAuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password_hash = hash_password("test-password")

    def setUp(self):
        self.user = SimpleNamespace(
            id=1, username="test-user", password_hash=self.password_hash,
            name="测试用户", role="teacher", status="active", subject="",
            supervisor_stage="",
        )
        self.db = MagicMock()
        self.db.query.return_value.filter.return_value.first.return_value = self.user
        self.db.get.return_value = self.user
        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        for name, value in (
            ("secret_key", "unit-test-signing-key-for-session-tests"),
            ("access_token_expire_minutes", 240),
            ("miniprogram_access_token_expire_minutes", 10080),
        ):
            context = patch.object(settings, name, value)
            context.start()
            self.addCleanup(context.stop)
        self.captcha = patch("app.auth.router.captcha_service.verify_captcha", return_value=True)
        self.captcha.start()
        self.addCleanup(self.captcha.stop)

    def login(self, **extra):
        return self.client.post("/api/auth/login", json={
            "username": "test-user", "password": "test-password",
            "captcha_id": "test-id", "captcha_code": "test-code", **extra,
        })

    def assert_lifetime(self, token, minutes):
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        remaining = payload["exp"] - datetime.now(timezone.utc).timestamp()
        self.assertAlmostEqual(remaining, minutes * 60, delta=3)
        return payload

    def test_miniprogram_lasts_seven_days_and_me_does_not_renew(self):
        response = self.login(client="miniprogram")
        self.assertEqual(response.status_code, 200)
        token = response.json()["access_token"]
        payload = self.assert_lifetime(token, 10080)
        headers = {"Authorization": f"Bearer {token}"}
        for offset, expected in ((-1, 200), (0, 401), (1, 401)):
            current = datetime.fromtimestamp(payload["exp"] + offset, timezone.utc)

            class Clock(datetime):
                @classmethod
                def now(cls, tz=None):
                    return current

            with patch("jwt.api_jwt.datetime", Clock):
                result = self.client.get("/api/auth/me", headers=headers)
            self.assertEqual(result.status_code, expected)
            self.assertNotIn("access_token", result.json())

    def test_web_default_and_explicit_web_keep_existing_lifetime(self):
        for extra in ({}, {"client": "web"}):
            response = self.login(**extra)
            self.assertEqual(response.status_code, 200)
            self.assert_lifetime(response.json()["access_token"], 240)

    def test_miniprogram_still_requires_captcha_and_password(self):
        self.assertEqual(self.login(client="miniprogram", captcha_code="").status_code, 400)
        self.assertEqual(self.login(client="miniprogram", password="wrong").status_code, 401)
        with patch("app.auth.router.captcha_service.verify_captcha", return_value=False):
            self.assertEqual(self.login(client="miniprogram").status_code, 400)

    def test_disabled_user_cannot_reuse_a_weekly_token(self):
        token = self.login(client="miniprogram").json()["access_token"]
        self.user.status = "disabled"
        self.assertEqual(self.login(client="miniprogram").status_code, 403)
        response = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 401)

    def test_wx_login_and_bind_also_issue_weekly_tokens(self):
        self.db.query.return_value.filter_by.return_value.first.return_value = SimpleNamespace(user_id=1)
        with patch("app.services.wx_service.jscode2session", new=AsyncMock(return_value=("test-openid", None))), \
                patch("app.services.student_case_service.audit"):
            response = self.client.post("/api/auth/wx-login", json={"code": "test-code"})
        self.assertEqual(response.status_code, 200)
        self.assert_lifetime(response.json()["access_token"], 10080)

        self.db.query.return_value.filter_by.return_value.first.return_value = None
        ticket = jwt.encode({
            "purpose": "wx_bind", "openid": "test-openid", "jti": "test-jti",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        }, settings.secret_key, algorithm=ALGORITHM)
        with patch("app.services.student_case_service.audit"):
            response = self.client.post("/api/auth/wx-bind", json={
                "bind_ticket": ticket, "username": "test-user", "password": "test-password",
            })
        self.assertEqual(response.status_code, 200)
        self.assert_lifetime(response.json()["access_token"], 10080)


if __name__ == "__main__":
    unittest.main()
