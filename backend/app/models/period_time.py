"""节次时间映射：配置每个节次对应的上课时间。"""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin


class PeriodTime(TimestampMixin, Base):
    __tablename__ = "period_times"

    id: Mapped[int] = mapped_column(primary_key=True)
    period: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    start_time: Mapped[str] = mapped_column(String(5))
    end_time: Mapped[str] = mapped_column(String(5))
