"""图形验证码服务：生成 4 位字母数字图片，一次性、5 分钟过期。

进程内内存存储；单实例/试点规模够用，多实例生产建议换 Redis。
"""

import base64
import io
import random
import socket
import threading
import time
import uuid
from urllib.parse import unquote, urlparse

from PIL import Image, ImageDraw, ImageFont

from app.core.config import settings

# 去掉易混淆字符 0/O/1/I
CHARSET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 4
EXPIRE_SECONDS = 5 * 60
MAX_STORE = 5000
KEY_PREFIX = "pfs:captcha:"

_store: dict[str, tuple[str, float]] = {}
_lock = threading.Lock()


class CaptchaStorageUnavailable(RuntimeError):
    """生产 Redis 不可用时的明确错误，调用方应返回可重试提示。"""


class RedisUnavailable(RuntimeError):
    """Redis 不可用或协议返回错误。"""


def _read_redis_response(reader):
    marker = reader.read(1)
    if not marker:
        raise RedisUnavailable("Redis 连接意外关闭")
    line = reader.readline().rstrip(b"\r\n")
    if marker == b"+":
        return line.decode("utf-8")
    if marker == b"-":
        raise RedisUnavailable(line.decode("utf-8", errors="replace"))
    if marker == b":":
        return int(line)
    if marker == b"$":
        size = int(line)
        if size == -1:
            return None
        data = reader.read(size)
        reader.read(2)
        return data.decode("utf-8")
    raise RedisUnavailable("Redis 返回了未知协议数据")


def _redis_command(*parts: str | int):
    """最小 Redis RESP 客户端，避免生产镜像因缺少第三方 redis 包而失效。"""
    redis_url = getattr(settings, "redis_url", "")
    if not redis_url:
        raise RedisUnavailable("未配置 REDIS_URL")
    parsed = urlparse(redis_url)
    if parsed.scheme != "redis" or not parsed.hostname:
        raise RedisUnavailable("REDIS_URL 配置无效")
    encoded = [str(part).encode("utf-8") for part in parts]
    request = b"*" + str(len(encoded)).encode() + b"\r\n" + b"".join(
        b"$" + str(len(part)).encode() + b"\r\n" + part + b"\r\n" for part in encoded
    )
    try:
        with socket.create_connection((parsed.hostname, parsed.port or 6379), timeout=0.5) as conn:
            conn.settimeout(0.5)
            with conn.makefile("rb") as reader:
                if parsed.password:
                    password = unquote(parsed.password)
                    auth = ("AUTH", unquote(parsed.username), password) if parsed.username else ("AUTH", password)
                    conn.sendall(_redis_request(*auth))
                    _read_redis_response(reader)
                database = parsed.path.strip("/")
                if database and database != "0":
                    conn.sendall(_redis_request("SELECT", database))
                    _read_redis_response(reader)
                conn.sendall(request)
                return _read_redis_response(reader)
    except (OSError, ValueError) as exc:
        raise RedisUnavailable("Redis 连接失败") from exc


def _redis_request(*parts: str | int) -> bytes:
    encoded = [str(part).encode("utf-8") for part in parts]
    return b"*" + str(len(encoded)).encode() + b"\r\n" + b"".join(
        b"$" + str(len(part)).encode() + b"\r\n" + part + b"\r\n" for part in encoded
    )


def _use_memory_fallback() -> bool:
    return settings.app_env.lower() in {"dev", "development", "test", "testing"}


def _storage_error(exc: Exception) -> CaptchaStorageUnavailable:
    error = CaptchaStorageUnavailable("验证码服务暂不可用，请稍后重试")
    error.__cause__ = exc
    return error


def _cleanup_locked(now: float) -> None:
    expired = [k for k, (_, exp) in _store.items() if exp < now]
    for k in expired:
        _store.pop(k, None)
    # 防内存无限增长
    if len(_store) > MAX_STORE:
        oldest = sorted(_store.items(), key=lambda kv: kv[1][1])[: len(_store) - MAX_STORE]
        for k, _ in oldest:
            _store.pop(k, None)


def _random_code() -> str:
    return "".join(random.choice(CHARSET) for _ in range(CODE_LENGTH))


def _draw_image(code: str) -> str:
    width, height = 120, 48
    bg = (random.randint(235, 255), random.randint(235, 255), random.randint(235, 255))
    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)
    try:
        # Pillow 内置位图字体，放大绘制
        font = ImageFont.load_default(size=28)
    except TypeError:
        font = ImageFont.load_default()

    # 逐字随机颜色/位置
    for i, ch in enumerate(code):
        x = 12 + i * 26 + random.randint(-2, 2)
        y = random.randint(4, 12)
        color = (random.randint(20, 120), random.randint(20, 120), random.randint(20, 120))
        draw.text((x, y), ch, fill=color, font=font)

    # 干扰线
    for _ in range(3):
        x1, y1 = random.randint(0, width), random.randint(0, height)
        x2, y2 = random.randint(0, width), random.randint(0, height)
        draw.line(
            [(x1, y1), (x2, y2)],
            fill=(random.randint(150, 200), random.randint(150, 200), random.randint(150, 200)),
            width=1,
        )
    # 干扰点
    for _ in range(40):
        draw.point(
            (random.randint(0, width - 1), random.randint(0, height - 1)),
            fill=(random.randint(150, 220), random.randint(150, 220), random.randint(150, 220)),
        )

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def create_captcha() -> tuple[str, str, str]:
    """返回 (captcha_id, code, image_base64)，答案存于共享 Redis。"""
    code = _random_code()
    image_b64 = _draw_image(code)
    captcha_id = uuid.uuid4().hex
    if getattr(settings, "redis_url", ""):
        try:
            _redis_command("SET", f"{KEY_PREFIX}{captcha_id}", code, "EX", EXPIRE_SECONDS)
        except RedisUnavailable as exc:
            if not _use_memory_fallback():
                raise _storage_error(exc)
        else:
            return captcha_id, code, image_b64

    now = time.time()
    with _lock:
        _cleanup_locked(now)
        _store[captcha_id] = (code, now + EXPIRE_SECONDS)
    return captcha_id, code, image_b64


def verify_captcha(captcha_id: str | None, code: str | None) -> bool:
    """大小写不敏感校验；Redis GETDEL 保证跨 worker 的一次性消费。"""
    if not captcha_id or not code:
        return False
    if getattr(settings, "redis_url", ""):
        try:
            # GETDEL 原子消费；TTL 完全由 Redis 控制，避免各应用进程的时钟差异。
            expected = _redis_command("GETDEL", f"{KEY_PREFIX}{captcha_id.strip()}")
        except RedisUnavailable as exc:
            if not _use_memory_fallback():
                raise _storage_error(exc)
        else:
            return expected is not None and expected.lower() == code.strip().lower()

    now = time.time()
    with _lock:
        saved = _store.pop(captcha_id.strip(), None)
        if saved is None:
            return False
        expected, exp = saved
        if exp < now:
            return False
        return expected.lower() == code.strip().lower()
