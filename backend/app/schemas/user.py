from pydantic import BaseModel, ConfigDict, Field

from app.models.user import ROLE_STUDENT, ROLES


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    name: str = Field(min_length=1, max_length=64)
    role: str = ROLE_STUDENT


class UserUpdate(BaseModel):
    name: str | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)
    status: str | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    name: str
    role: str
    status: str
