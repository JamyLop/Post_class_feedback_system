from pydantic import BaseModel, ConfigDict, Field, field_validator


class TransferRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_username: str = Field(min_length=1, max_length=64)
    student_name: str = Field(default="", max_length=64)
    source_class_id: int | None = Field(default=None, gt=0)
    target_class_id: int = Field(gt=0)
    # 一生一案可能有多个活动周期；每个学科的接手老师应在所有周期一致。
    subject_teachers: dict[str, int] = Field(default_factory=dict)

    @field_validator("student_username", "student_name")
    @classmethod
    def strip_text(cls, value):
        return value.strip()


class TransferPreviewIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rows: list[TransferRow] = Field(min_length=1, max_length=500)


class TransferCommitIn(TransferPreviewIn):
    request_id: str = Field(min_length=16, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    preview_token: str = Field(min_length=64, max_length=64)
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason")
    @classmethod
    def reason_required(cls, value):
        if not value.strip():
            raise ValueError("请填写调班原因")
        return value.strip()
