from app.core.database import Base  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.class_ import Class, ClassStudent, ClassTeacher, StudentGuardian, StudentConsultant  # noqa: F401
from app.models.assignment import Assignment, AssignmentQuestion  # noqa: F401
from app.models.question import Question, QuestionKnowledgePoint  # noqa: F401
from app.models.knowledge import (  # noqa: F401
    KnowledgePoint,
    StudentKnowledgeRecord,
    StudentKnowledgeStat,
)
from app.models.submission import Submission, SubmissionAnswer  # noqa: F401
from app.models.grading import GradingResult, GradingPromptVersion  # noqa: F401
from app.models.feedback import FeedbackReport  # noqa: F401
from app.models.invite import InviteCode  # noqa: F401
from app.models.student_case import (  # noqa: F401
    CaseAuditLog,
    CaseCycle,
    CaseDiagnosis,
    CaseEvidenceLink,
    CaseGoal,
    CaseImportBatch,
    CaseImportDocument,
    CaseReview,
    CaseStudentProfile,
    CaseTask,
    CaseVersion,
    StudentCase,
    SubjectPlan,
    SubjectSuggestion,
    TaskCheckin,
)
from app.models.weekly_score import WeeklyTestScore  # noqa: F401
from app.models.monthly_report import MonthlyReport  # noqa: F401
from app.models.user_external_identity import UserExternalIdentity  # noqa: F401
