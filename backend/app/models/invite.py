from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampMixin
from app.core.database import Base

INVITE_STATUS_ACTIVE = "active"
INVITE_STATUS_USED = "used"
INVITE_STATUS_DISABLED = "disabled"


class InviteCode(TimestampMixin, Base):
    """注册邀请码：teacher / student 角色注册必须携带，管理员创建。"""

    __tablename__ = "invite_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(16), index=True)
    status: Mapped[str] = mapped_column(
        String(16), default=INVITE_STATUS_ACTIVE, index=True
    )
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # 使用次数限制：默认 1（一次性，兼容老行为）；used_count 满 max_uses 后 status 才置为 used
    max_uses: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))
    used_count: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    used_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)