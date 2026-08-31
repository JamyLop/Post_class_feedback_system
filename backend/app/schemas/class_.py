from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


EducationStage = Literal["初中", "高中"]
ClassType = Literal["短期班", "全年班", "集训班", "1V1"]
ShortTermType = Literal["暑假班", "寒假班"]


def validate_class_category(
    education_stage: str,
    grade: str,
    class_type: str,
    short_term_type: str | None,
) -> None:
    """校验班级分类的联动规则，防止绕过前端提交非法组合。"""
    stage_grades = {
        "初中": {"初一", "初二", "初三"},
        "高中": {"高一", "高二", "高三"},
    }
    if grade not in stage_grades[education_stage]:
        raise ValueError(f"{education_stage}不能选择年级“{grade}”")
    if class_type == "集训班" and education_stage != "高中":
        raise ValueError("集训班仅限高中")
    if class_type == "短期班" and short_term_type is None:
        raise ValueError("短期班必须选择暑假班或寒假班")
    if class_type != "短期班" and short_term_type is not None:
        raise ValueError("只有短期班可以设置暑假班或寒假班")


class ClassCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    education_stage: EducationStage
    grade: str = Field(min_length=1, max_length=32)
    class_type: ClassType
    short_term_type: ShortTermType | None = None
    school_year: str = Field(default="2026-2027", min_length=4, max_length=16)

    @model_validator(mode="after")
    def validate_category(self):
        validate_class_category(
            self.education_stage, self.grade, self.class_type, self.short_term_type
        )
        return self


class ClassUpdate(BaseModel):
    name: str | None = None
    education_stage: EducationStage | None = None
    grade: str | None = None
    class_type: ClassType | None = None
    short_term_type: ShortTermType | None = None
    school_year: str | None = Field(default=None, min_length=4, max_length=16)


class ClassOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    education_stage: EducationStage
    grade: str
    class_type: ClassType
    short_term_type: ShortTermType | None
    school_year: str
    teacher_id: int


class StudentAdd(BaseModel):
    student_ids: list[int] = Field(min_length=1)


class ClassStudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    name: str
