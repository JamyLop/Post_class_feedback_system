from pydantic import BaseModel, ConfigDict, Field


class TimetableEntryCreate(BaseModel):
    class_id: int
    teacher_id: int
    subject: str = Field(min_length=1, max_length=32)
    weekday: int = Field(ge=1, le=7)
    period: int = Field(ge=1, le=12)
    classroom: str = Field(default="", max_length=64)


class TimetableEntryUpdate(BaseModel):
    class_id: int | None = None
    teacher_id: int | None = None
    subject: str | None = Field(default=None, min_length=1, max_length=32)
    weekday: int | None = Field(default=None, ge=1, le=7)
    period: int | None = Field(default=None, ge=1, le=12)
    classroom: str | None = Field(default=None, max_length=64)


class TimetableEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    class_id: int
    class_name: str = ""
    teacher_id: int
    teacher_name: str = ""
    subject: str
    weekday: int
    period: int
    classroom: str
    start_time: str = ""
    end_time: str = ""
