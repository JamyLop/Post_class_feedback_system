from datetime import datetime

from pydantic import BaseModel


class KnowledgeStatOut(BaseModel):
    knowledge_point_id: int
    name: str
    code: str
    chapter: str
    correct_count: int
    wrong_count: int
    mastery_score: float
    trend: str
    last_updated: datetime


class WeakPointOut(BaseModel):
    knowledge_point_id: int
    name: str
    code: str
    chapter: str
    correct_count: int
    wrong_count: int
    mastery_score: float
    trend: str


class TrendPointOut(BaseModel):
    assignment_id: int
    submission_id: int
    total_score: float
    max_total: float
    percent: float
    submitted_at: datetime


class LearningTrendOut(BaseModel):
    points: list[TrendPointOut]


class QuestionAccuracyOut(BaseModel):
    question_id: int
    question_type: str
    content: str
    max_score: float
    accuracy: float
    answer_count: int


class AssignmentWeakPointOut(BaseModel):
    knowledge_point_id: int
    name: str
    code: str
    chapter: str
    correct_count: int
    wrong_count: int
    mastery_score: float


class ErrorTypeCountOut(BaseModel):
    error_type: str
    count: int


class AssignmentAnalysisOut(BaseModel):
    assignment_id: int
    submission_count: int
    average_score: float
    pass_rate: float
    score_distribution: dict[str, int]
    question_accuracy: list[QuestionAccuracyOut]
    weak_knowledge_points: list[AssignmentWeakPointOut]
    common_errors: list[ErrorTypeCountOut]


class UnsubmittedStudentOut(BaseModel):
    student_id: int
    name: str


class ClassAnalyticsOut(BaseModel):
    class_id: int
    submission_count: int
    average_score: float
    score_distribution: dict[str, int]
    knowledge_accuracy: list[AssignmentWeakPointOut]
    weak_knowledge_points: list[AssignmentWeakPointOut]
    common_errors: list[ErrorTypeCountOut]
    unsubmitted_students: list[UnsubmittedStudentOut]
