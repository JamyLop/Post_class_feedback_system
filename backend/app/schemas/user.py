from pydantic import BaseModel, ConfigDict, Field

from app.models.user import ROLE_STUDENT, ROLES


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    name: str = Field(min_length=1, max_length=64)
    role: str = ROLE_STUDENT
    channel: str = Field(default="", max_length=64)


class UserUpdate(BaseModel):
    name: str | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)
    status: str | None = None
    channel: str | None = Field(default=None, max_length=64)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    name: str
    role: str
    status: str
    channel: str = ""
    dorm_number: str = ""


class QuickStudentCreate(BaseModel):
    """免班级快捷新建学生：只录档案信息，不入班，账号自动生成。

    适用于咨询老师先建学生、后续由班主任从已有学生中挑入班级的流程。
    """

    name: str = Field(min_length=1, max_length=64, description="学生姓名")
    gender: str = Field(default="", max_length=16, description="性别")
    ethnicity: str = Field(default="", max_length=32, description="民族")
    grade: str = Field(default="", max_length=32, description="年级")
    source_school: str = Field(default="", max_length=128, description="生源地学校")
    channel: str = Field(default="", max_length=64, description="生源渠道")
    dorm_number: str = Field(default="", max_length=32, description="宿舍号")
    consultant_id: int | None = Field(default=None, description="咨询老师ID（选填）")
