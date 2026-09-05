"""Redis 客户端（单例，按需使用）。"""

import redis

from app.core.config import settings

redis_client = redis.Redis.from_url(
    settings.redis_url, decode_responses=True
)


def get_redis():
    """获取共享 Redis 客户端实例。"""
    return redis_client
