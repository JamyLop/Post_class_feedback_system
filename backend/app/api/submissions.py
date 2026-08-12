import json

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.core.database import get_db
from app.models.assignment import (
    ASSIGNMENT_STATUS_PUBLISHED,
    Assignment,
    AssignmentQuestion,
)
from app.models.class_ import ClassStudent
from app.models.question import Question
from app.models.submission import (
    SUBMISSION_STATUS_PROCESSING,
    SUBMISSION_STATUS_SUBMITTED,
    Submission,
    SubmissionAnswer,
)
from app.models.user import ROLE_STUDENT, ROLE_TEACHER, User
from app.schemas.submission import SubmissionOut
from app.storage import upload_bytes
from app.tasks.grading_tasks import grade_submission
from app.tasks.ocr_tasks import ocr_submission

router = APIRouter(tags=["submissions"])

ALLOWED_TYPES = {"text", "image", "pdf"}
EXT_MAP = {"image": ".png", "pdf": ".pdf"}


def _ensure_student(user: User) -> None:
    if user.role != ROLE_STUDENT:
        raise HTTPException(status_code=403, detail="仅学生可提交作业")


def _ensure_member(db: Session, assignment: Assignment, user: User) -> None:
    member = (
        db.query(ClassStudent)
        .filter(
            ClassStudent.class_id == assignment.class_id,
            ClassStudent.student_id == user.id,
        )
        .first()
    )
    if member is None:
        raise HTTPException(status_code=403, detail="你不属于该作业所在班级")


@router.post(
    "/assignments/{assignment_id}/submit", response_model=SubmissionOut
)
def submit_assignment(
    assignment_id: int,
    content_type: str = Form(...),
    content_text: str | None = Form(default=None),
    answers_json: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _ensure_student(user)
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="无效的提交类型")

    assignment = db.get(Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="作业不存在")
    if assignment.status != ASSIGNMENT_STATUS_PUBLISHED:
        raise HTTPException(status_code=400, detail="作业未发布或已关闭")
    _ensure_member(db, assignment, user)

    # 覆盖式提交：删除该学生此前提交，重新生成
    old = (
        db.query(Submission)
        .filter(
            Submission.assignment_id == assignment_id,
            Submission.student_id == user.id,
        )
        .first()
    )
    if old is not None:
        db.delete(old)
        db.flush()

    submission = Submission(
        assignment_id=assignment_id,
        student_id=user.id,
        content_type=content_type,
        status=SUBMISSION_STATUS_SUBMITTED,
    )

    if content_type == "text":
        if not content_text:
            raise HTTPException(status_code=400, detail="文本提交缺少内容")
        submission.content_url = ""
        db.add(submission)
        db.flush()
        _create_answers(db, submission, answers_json, content_text)
    else:
        if file is None:
            raise HTTPException(status_code=400, detail="请上传作业文件")
        data = file.file.read()
        if not data:
            raise HTTPException(status_code=400, detail="上传文件为空")
        key = upload_bytes(
            data,
            file.content_type or "application/octet-stream",
            EXT_MAP.get(content_type, ""),
        )
        submission.content_url = key
        submission.status = SUBMISSION_STATUS_PROCESSING
        db.add(submission)
        db.flush()
        _create_answers(db, submission, answers_json, None)

    db.commit()
    db.refresh(submission)

    if content_type in ("image", "pdf"):
        # OCR 完成后由 ocr_submission 任务接着触发批改，避免竞态
        ocr_submission.delay(submission.id)
    else:
        grade_submission.delay(submission.id)

    return submission


def _create_answers(
    db: Session,
    submission: Submission,
    answers_json: str | None,
    fallback_text: str | None,
) -> None:
    """创建逐题答案记录。image/pdf 提交时由 OCR（阶段 3）切分补全。"""
    question_ids = [
        aq.question_id
        for aq in db.query(AssignmentQuestion)
        .filter(AssignmentQuestion.assignment_id == submission.assignment_id)
        .order_by(AssignmentQuestion.question_order.asc())
        .all()
    ]
    answers: list[dict] = []
    if answers_json:
        try:
            parsed = json.loads(answers_json)
            if isinstance(parsed, list):
                answers = [a for a in parsed if isinstance(a, dict)]
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="answers_json 格式错误")

    by_question = {a.get("question_id"): a.get("student_answer", "") for a in answers}

    for qid in question_ids:
        # 显式作答（含留空=未作答）优先；answers_json 中未列出的题目回退到整卷文本
        value = by_question[qid] if qid in by_question else (fallback_text or "")
        db.add(
            SubmissionAnswer(
                submission_id=submission.id,
                question_id=qid,
                student_answer=value,
                max_score=db.get(Question, qid).score if db.get(Question, qid) else None,
            )
        )


@router.get("/submissions/{submission_id}", response_model=SubmissionOut)
def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    submission = db.get(Submission, submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="提交记录不存在")
    if user.role == ROLE_STUDENT and submission.student_id != user.id:
        raise HTTPException(status_code=403, detail="无权查看该提交")
    return submission


@router.get(
    "/assignments/{assignment_id}/submissions", response_model=list[SubmissionOut]
)
def list_submissions(
    assignment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    assignment = db.get(Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="作业不存在")
    if user.role == ROLE_STUDENT:
        # 学生只返回自己的提交
        return (
            db.query(Submission)
            .filter(
                Submission.assignment_id == assignment_id,
                Submission.student_id == user.id,
            )
            .all()
        )
    if user.role == ROLE_TEACHER and assignment.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="无权查看该作业的提交")
    return (
        db.query(Submission)
        .filter(Submission.assignment_id == assignment_id)
        .order_by(Submission.submitted_at.desc())
        .all()
    )
