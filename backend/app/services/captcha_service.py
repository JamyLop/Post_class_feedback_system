"""图形验证码服务：生成 4 位字母数字图片，一次性、5 分钟过期。

进程内内存存储；单实例/试点规模够用，多实例生产建议换 Redis。
"""

import base64
import io
import random
import threading
import time
import uuid

from PIL import Image, ImageDraw, ImageFont

# 去掉易混淆字符 0/O/1/I
CHARSET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 4
EXPIRE_SECONDS = 5 * 60
MAX_STORE = 5000

_store: dict[str, tuple[str, float]] = {}
_lock = threading.Lock()


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
    """返回 (captcha_id, code, image_base64)。code 仅服务端持有，不直接返回给客户端的值由调用方决定。"""
    code = _random_code()
    image_b64 = _draw_image(code)
    captcha_id = uuid.uuid4().hex
    now = time.time()
    with _lock:
        _cleanup_locked(now)
        _store[captcha_id] = (code, now + EXPIRE_SECONDS)
    return captcha_id, code, image_b64


def verify_captcha(captcha_id: str | None, code: str | None) -> bool:
    """大小写不敏感校验，一次性消费（无论对错都删除，防止暴力破解）。"""
    if not captcha_id or not code:
        return False
    now = time.time()
    with _lock:
        saved = _store.pop(captcha_id.strip(), None)
        if saved is None:
            return False
        expected, exp = saved
        if exp < now:
            return False
        return expected.lower() == code.strip().lower()
