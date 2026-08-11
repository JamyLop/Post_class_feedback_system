from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AnswerIn(BaseModel):
    question_id: int
    student_answer: str = ""


class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    assignment_id: int
    student_id: int
    content_type: str
    content_url: str
    status: str
    submitted_at: datetime
