from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str
    password: str
    captcha_id: str = ""
    captcha_code: str = ""
    client: Literal["web", "miniprogram"] = "web"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    name: str
    role: str
    status: str = "active"
    subject: str = ""
    supervisor_stage: str = ""


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6)
