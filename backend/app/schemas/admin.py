from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    name: str = Field(min_length=1, max_length=64)
    role: str
    invite_code: str = Field(min_length=1, max_length=16)
    subject: Optional[str] = Field(default=None, max_length=32)
    captcha_id: str = ""
    captcha_code: str = ""


class InviteCodeCreate(BaseModel):
    role: str
    expires_at: Optional[datetime] = None
    max_uses: int = Field(default=1, ge=1, le=10000)


class InviteCodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    role: str
    status: str
    expires_at: Optional[datetime] = None
    max_uses: int = 1
    used_count: int = 0
    used_by: Optional[int] = None
    used_at: Optional[datetime] = None
    created_at: datetime


class AdminStats(BaseModel):
    user_count: int
    admin_count: int
    teacher_count: int
    student_count: int
    parent_count: int
    deyu_director_count: int = 0
    consultant_count: int = 0
    subject_teacher_count: int = 0
    class_count: int
    case_count: int = 0


class GuardianLinkCreate(BaseModel):
    parent_id: int
    student_id: int
    relationship: str = Field(default="guardian", min_length=1, max_length=24)


class GuardianLinkOut(GuardianLinkCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    parent_name: str = ""
    student_name: str = ""
    created_at: datetime


class ConsultantLinkCreate(BaseModel):
    consultant_id: int
    student_id: int


class ConsultantLinkOut(ConsultantLinkCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    consultant_name: str = ""
    consultant_username: str = ""
    student_name: str = ""
    student_username: str = ""
    student_channel: str = ""
    created_at: datetime


class ClassTeacherLinkCreate(BaseModel):
    class_id: int
    teacher_id: int
    subject: str = Field(min_length=1, max_length=32)


class ClassTeacherLinkOut(ClassTeacherLinkCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str = ""
    teacher_name: str = ""
    teacher_username: str = ""
    class_name: str = ""
    created_at: datetime
