from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampMixin
from app.core.database import Base

# 系统角色与状态常量
# 校长 = admin（系统管理员/督查最高权限），德育主任 = deyu_director（审核班主任方案），班主任 = teacher，咨询老师 = consultant，家长/学生只读
ROLE_ADMIN = "admin"
ROLE_TEACHER = "teacher"
ROLE_DEYU_DIRECTOR = "deyu_director"
ROLE_STUDENT = "student"
ROLE_PARENT = "parent"
ROLE_CONSULTANT = "consultant"
ROLES = [ROLE_ADMIN, ROLE_TEACHER, ROLE_DEYU_DIRECTOR, ROLE_STUDENT, ROLE_PARENT, ROLE_CONSULTANT]

# 中文标签（用于前端展示与管理台统计）
ROLE_LABELS = {
    ROLE_ADMIN: "校长",
    ROLE_TEACHER: "班主任",
    ROLE_DEYU_DIRECTOR: "德育主任",
    ROLE_STUDENT: "学生",
    ROLE_PARENT: "家长",
    ROLE_CONSULTANT: "咨询老师",
}

USER_STATUS_ACTIVE = "active"
USER_STATUS_DISABLED = "disabled"


class User(TimestampMixin, Base):
    """用户表：管理员、教师、学生和家长账号，含 bcrypt 密码哈希。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(16), index=True)
    status: Mapped[str] = mapped_column(String(16), default=USER_STATUS_ACTIVE)
    # 学生档案扩展（班主任新建学生时录入，无需手动维护账号）
    gender: Mapped[str] = mapped_column(String(16), default="", server_default="")
    ethnicity: Mapped[str] = mapped_column(String(32), default="", server_default="")
    source_school: Mapped[str] = mapped_column(String(128), default="", server_default="")
    grade: Mapped[str] = mapped_column(String(32), default="", server_default="")
