from pydantic import BaseModel, ConfigDict, Field


class ClassCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    grade: str = Field(min_length=1, max_length=32)


class ClassUpdate(BaseModel):
    name: str | None = None
    grade: str | None = None


class ClassOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    grade: str
    teacher_id: int


class StudentAdd(BaseModel):
    student_ids: list[int] = Field(min_length=1)


class ClassStudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    name: str
