"""批量调班记录只追加，保留当时的名单、责任人与交接快照。"""
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ClassTransferBatch(Base):
    __tablename__ = "class_transfer_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[str] = mapped_column(String(64), unique=True)
    payload_hash: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(Text)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    actor_name: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class ClassTransferItem(Base):
    __tablename__ = "class_transfer_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("class_transfer_batches.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    student_username: Mapped[str] = mapped_column(String(64))
    student_name: Mapped[str] = mapped_column(String(64))
    source_class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), index=True)
    target_class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), index=True)
    source_class_name: Mapped[str] = mapped_column(String(64))
    target_class_name: Mapped[str] = mapped_column(String(64))
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    detail: Mapped[Any] = mapped_column(JSON, default=dict)
