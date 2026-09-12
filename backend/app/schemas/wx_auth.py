"""微信登录绑定相关 schemas。"""

from pydantic import BaseModel


class WxLoginRequest(BaseModel):
    code: str


class WxLoginBoundResponse(BaseModel):
    access_token: str
    user: dict


class WxLoginNeedBindResponse(BaseModel):
    bind_ticket: str
    bind_expires_in: int = 300


class WxBindRequest(BaseModel):
    bind_ticket: str
    username: str | None = None
    password: str | None = None
    # 邀请码注册分支（可选）
    invite_code: str | None = None
    role: str | None = None
    name: str | None = None


class ChildBrief(BaseModel):
    student_id: int
    student_name: str
    class_id: int | None = None
    class_name: str | None = None
    cycle_name: str | None = None
    latest_case_id: int | None = None
    latest_case_status: str | None = None
    latest_case_summary: str | None = None
    latest_case_version: int | None = None
