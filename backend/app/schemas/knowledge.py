from pydantic import BaseModel, ConfigDict, Field


class KnowledgePointCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=32)
    grade: str = Field(min_length=1, max_length=32)
    chapter: str = Field(default="", max_length=64)
    name: str = Field(min_length=1, max_length=64)
    code: str = Field(min_length=1, max_length=64)
    parent_id: int | None = None


class KnowledgePointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject: str
    grade: str
    chapter: str
    name: str
    code: str
    parent_id: int | None = None


class KnowledgePointTreeNode(BaseModel):
    id: int
    name: str
    code: str
    chapter: str
    children: list["KnowledgePointTreeNode"] = []
