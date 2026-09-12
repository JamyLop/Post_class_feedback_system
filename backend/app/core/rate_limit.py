"""轻量内存限流：上线前堵住登录/注册爆破口，无需新增依赖。

生产多实例建议换 Redis 共享计数（网关限流优先），本模块 fail-open：异常不拦请求。
"""

import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse

# path 前缀 -> (窗口秒, 最大次数)
AUTH_LIMITS: dict[str, tuple[int, int]] = {
    "/api/auth/login": (60, 20),
    "/api/auth/register": (60, 10),
    "/api/auth/captcha": (60, 60),
    "/api/auth/wx-login": (60, 30),
    "/api/auth/wx-bind": (60, 30),
    "/api/case-tasks/batch-checkin": (60, 10),
}

DEFAULT_LIMIT = (60, 120)

_hits: dict[str, deque] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _rule(path: str) -> tuple[int, int]:
    for prefix, rule in AUTH_LIMITS.items():
        if path.startswith(prefix):
            return rule
    return DEFAULT_LIMIT


async def rate_limit_middleware(request: Request, call_next):
    # 仅限 API 请求，健康探针放行
    if not request.url.path.startswith("/api/"):
        return await call_next(request)
    if request.url.path in ("/api/health", "/api/ready"):
        return await call_next(request)
    try:
        window, limit = _rule(request.url.path)
        now = time.monotonic()
        key = f"{_client_ip(request)}|{request.url.path.rsplit('/', 1)[0] if request.url.path.startswith('/api/auth/') else request.url.path}"
        dq = _hits[key]
        while dq and dq[0] <= now - window:
            dq.popleft()
        if len(dq) >= limit:
            return JSONResponse(status_code=429, content={"detail": "请求过于频繁，请稍后再试"})
        dq.append(now)
        # 防止内存无限增长：定期清理空 key（低频触发即可）
        if len(_hits) > 20000:
            _hits.clear()
    except Exception:
        pass
    return await call_next(request)
