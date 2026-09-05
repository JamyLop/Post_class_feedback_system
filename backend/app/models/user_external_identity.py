"""微信/外部身份绑定表：解耦 users 与微信 openid。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserExternalIdentity(Base):
    """用户外部身份： provider=wechat_miniprogram, subject_id=openid """

    __tablename__ = "user_external_identities"
    __table_args__ = (
        UniqueConstraint("provider", "app_id", "subject_id", name="uq_provider_app_subject"),
        UniqueConstraint("provider", "user_id", name="uq_provider_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(32), default="wechat_miniprogram", index=True)
    app_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    subject_id: Mapped[str] = mapped_column(String(128), index=True)  # openid
    unionid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    bound_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
