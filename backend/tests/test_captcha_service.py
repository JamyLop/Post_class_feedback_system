import pytest

from app.services import captcha_service


class FakeRedis:
    def __init__(self):
        self.values = {}

    def command(self, command, key, *args):
        if command == "SET":
            value = args[0]
            self.values[key] = value
            return "OK"
        if command == "GETDEL":
            return self.values.pop(key, None)
        raise AssertionError(command)

def test_redis_captcha_is_shared_and_consumed_once(monkeypatch):
    """答案位于共享存储，任意 worker 都能校验且只能校验一次。"""
    fake = FakeRedis()
    monkeypatch.setattr(captcha_service, "_redis_command", fake.command)
    monkeypatch.setattr(captcha_service.settings, "redis_url", "redis://shared")

    captcha_id, code, _ = captcha_service.create_captcha()

    assert captcha_service.verify_captcha(captcha_id, code)
    assert not captcha_service.verify_captcha(captcha_id, code)


def test_production_does_not_silently_fallback_when_redis_fails(monkeypatch):
    class BrokenRedis:
        def command(self, *args):
            raise captcha_service.RedisUnavailable("unavailable")

    monkeypatch.setattr(captcha_service, "_redis_command", BrokenRedis().command)
    monkeypatch.setattr(captcha_service.settings, "app_env", "production")
    monkeypatch.setattr(captcha_service.settings, "redis_url", "redis://shared")

    with pytest.raises(captcha_service.CaptchaStorageUnavailable):
        captcha_service.create_captcha()
