"""微信 jscode2session 封装，支持 mock 与生产校验。"""

import logging
from typing import Tuple

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


async def jscode2session(code: str) -> Tuple[str, str | None]:
    """
    返回 (openid, unionid|None)
    - 若 WX_MOCK=true 且 code 以 mock: 开头，直接返回模拟 openid（便于本地与 CI 测试）
    - 否则调微信接口 https://api.weixin.qq.com/sns/jscode2session
    """
    if settings.wx_mock and code.startswith("mock:"):
        mock_openid = code[len("mock:"):].strip() or "mock_openid_default"
        # mock unionid 不提供
        return mock_openid, None

    if not settings.wx_appid or not settings.wx_secret:
        # 生产应关闭登录并记录脱敏错误，禁止自动回退 mock
        logger.error("wx jscode2session called without WX_APPID/WX_SECRET configured")
        raise ValueError("微信登录未配置")

    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": settings.wx_appid,
        "secret": settings.wx_secret,
        "js_code": code,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        data = resp.json()
    if data.get("errcode") not in (None, 0):
        logger.warning("wx jscode2session failed errcode=%s errmsg=%s", data.get("errcode"), data.get("errmsg"))
        raise ValueError(data.get("errmsg") or "微信登录失败")
    openid = data.get("openid")
    if not openid:
        raise ValueError("微信未返回 openid")
    return openid, data.get("unionid")
