from pydantic import BaseModel, ConfigDict, Field


class ClassCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    grade: str = Field(min_length=1, max_length=32)
    school_year: str = Field(default="2026-2027", min_length=4, max_length=16)


class ClassUpdate(BaseModel):
    name: str | None = None
    grade: str | None = None
    school_year: str | None = Field(default=None, min_length=4, max_length=16)


class ClassOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    grade: str
    school_year: str
    teacher_id: int


class StudentAdd(BaseModel):
    student_ids: list[int] = Field(min_length=1)


class ClassStudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    name: str
