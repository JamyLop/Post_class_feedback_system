import re

from pydantic import BaseModel, ConfigDict, Field, model_validator


TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class PeriodTimeUpdate(BaseModel):
    start_time: str = Field(min_length=5, max_length=5)
    end_time: str = Field(min_length=5, max_length=5)

    @model_validator(mode="after")
    def validate_times(self):
        if not TIME_PATTERN.match(self.start_time):
            raise ValueError("开始时间格式无效，应为 HH:MM（如 08:00）")
        if not TIME_PATTERN.match(self.end_time):
            raise ValueError("结束时间格式无效，应为 HH:MM（如 08:45）")
        if self.start_time >= self.end_time:
            raise ValueError("开始时间必须早于结束时间")
        return self


class PeriodTimeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    period: int
    start_time: str
    end_time: str
