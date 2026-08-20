from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampMixin
from app.core.database import Base

# 系统角色与状态常量
ROLE_ADMIN = "admin"
ROLE_TEACHER = "teacher"
ROLE_STUDENT = "student"
ROLES = [ROLE_ADMIN, ROLE_TEACHER, ROLE_STUDENT]

USER_STATUS_ACTIVE = "active"
USER_STATUS_DISABLED = "disabled"


class User(TimestampMixin, Base):
    """用户表：管理员/教师/学生三种角色，含 bcrypt 密码哈希。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(16), index=True)
    status: Mapped[str] = mapped_column(String(16), default=USER_STATUS_ACTIVE)
