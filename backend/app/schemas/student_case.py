from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CaseCycleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    school_year: str = Field(min_length=4, max_length=16)
    starts_on: date
    ends_on: date

    @model_validator(mode="after")
    def validate_dates(self):
        if self.ends_on < self.starts_on:
            raise ValueError("周期结束日期不能早于开始日期")
        return self


class CaseCycleOut(CaseCycleCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    grade: str
    is_active: bool


class StudentCaseCreate(BaseModel):
    cycle_id: int
    student_id: int
    class_id: int
    owner_teacher_id: int
    overall_problem: str = ""
    admission_target: str = ""
    current_summary: str = ""


class StudentCaseUpdate(BaseModel):
    overall_problem: str | None = None
    admission_target: str | None = None
    current_summary: str | None = None
    owner_teacher_id: int | None = None
    change_reason: str = Field(default="", max_length=500)


class StudentCaseTransition(BaseModel):
    target_status: Literal[
        "draft", "pending_confirmation", "executing", "pending_review", "adjusted", "archived"
    ]
    reason: str = Field(default="", max_length=500)


class StudentCaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    cycle_id: int
    student_id: int
    class_id: int
    owner_teacher_id: int
    overall_problem: str
    admission_target: str
    current_summary: str
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    student_name: str | None = None
    class_name: str | None = None


class CaseStudentProfileUpsert(BaseModel):
    student_name: str = Field(default="", max_length=64)
    gender: str = Field(default="", max_length=16)
    ethnicity: str = Field(default="", max_length=32)
    source_school: str = Field(default="", max_length=128)
    grade: str = Field(default="", max_length=32)
    parent_evaluation: str = Field(default="", max_length=4000)
    primary_needs: str = Field(default="", max_length=4000)
    allergy_history: str = Field(default="", max_length=2000)
    underlying_conditions: str = Field(default="", max_length=2000)
    other_health_notes: str = Field(default="", max_length=2000)


class CaseStudentProfileOut(CaseStudentProfileUpsert):
    model_config = ConfigDict(from_attributes=True)
    id: int | None = None
    student_case_id: int


class CaseVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_case_id: int
    version: int
    snapshot: Any
    change_reason: str
    created_by: int
    created_at: datetime


class SubjectPlanUpsert(BaseModel):
    subject: str = Field(min_length=1, max_length=32)
    teacher_id: int
    problem_location: str = ""
    cause_analysis: str = ""
    struggle_goal: str = ""
    gaokao_requirement: str = ""
    reinforcement: str = ""


class SubjectPlanOut(SubjectPlanUpsert):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_case_id: int
    status: str


class CaseGoalCreate(BaseModel):
    goal_type: Literal["gaokao_total", "stage_total", "subject_score", "knowledge_block"]
    subject: str = Field(default="", max_length=32)
    title: str = Field(min_length=1, max_length=128)
    baseline_value: float | None = None
    target_value: float | None = None
    deadline: date | None = None


class CaseGoalOut(CaseGoalCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_case_id: int
    status: str


class CaseTaskCreate(BaseModel):
    subject: str = Field(default="", max_length=32)
    title: str = Field(min_length=1, max_length=160)
    description: str = ""
    cadence: Literal["daily", "weekly", "monthly"]
    starts_on: date
    due_on: date

    @model_validator(mode="after")
    def validate_dates(self):
        if self.due_on < self.starts_on:
            raise ValueError("任务截止日期不能早于开始日期")
        return self


class CaseTaskOut(CaseTaskCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_case_id: int
    status: str
    created_by: int


class TaskCheckinCreate(BaseModel):
    completion_rate: int = Field(ge=0, le=100)
    self_check: str = Field(default="", max_length=2000)


class TaskCheckinOut(TaskCheckinCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    task_id: int
    student_id: int
    checked_in_at: datetime


class CaseReviewCreate(BaseModel):
    task_id: int | None = None
    review_level: Literal["subject", "head_teacher", "school", "principal"]
    subject: str = Field(default="", max_length=32)
    problem: str = Field(default="", max_length=4000)
    corrective_action: str = Field(default="", max_length=4000)
    correction_due_on: date | None = None
    recheck_result: str = Field(default="", max_length=4000)


class CaseReviewOut(CaseReviewCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_case_id: int
    reviewer_id: int
    reviewed_at: datetime


class StudentCaseDetail(StudentCaseOut):
    viewer_role: str = ""
    can_manage: bool = False
    student_profile: CaseStudentProfileOut
    subject_plans: list[SubjectPlanOut] = []
    goals: list[CaseGoalOut] = []
    tasks: list[CaseTaskOut] = []
    task_checkins: list[TaskCheckinOut] = []
    reviews: list[CaseReviewOut] = []


class CaseProgressOut(BaseModel):
    total: int
    draft: int
    pending_confirmation: int
    executing: int
    pending_review: int
    adjusted: int
    archived: int
    overdue_tasks: int
    long_unreviewed: int


class CaseImportBatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    batch_key: str
    scope_grade: str
    source_root: str
    selected_students: Any
    status: str
    summary: Any
    created_by: int
    created_at: datetime
    finished_at: datetime | None


class CaseImportDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    batch_id: int
    student_case_id: int | None
    detected_student_name: str
    detected_subject: str
    original_path: str
    original_filename: str
    file_ext: str
    file_hash: str
    source_version: int
    file_size: int
    parsed_fields: Any
    status: str
    conflict_reason: str
    imported_at: datetime
