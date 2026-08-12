import json
import logging
from datetime import datetime, timezone

from celery.exceptions import Retry
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
from app.core.config import settings
from app.core.database import get_db
from app.models.assignment import (
    ASSIGNMENT_STATUS_PUBLISHED,
    Assignment,
    AssignmentQuestion,
)
from app.models.class_ import ClassStudent
from app.models.question import Question
from app.models.grading import GRADING_STATUS_CONFIRMED, GradingResult
from app.models.submission import (
    SUBMISSION_STATUS_COMPLETED,
    SUBMISSION_STATUS_FAILED,
    SUBMISSION_STATUS_PROCESSING,
    SUBMISSION_STATUS_SUBMITTED,
    SUBMISSION_STATUS_TEACHER_REVIEWED,
    Submission,
    SubmissionAnswer,
)
from app.models.user import ROLE_ADMIN, ROLE_STUDENT, ROLE_TEACHER, User
from app.schemas.submission import SubmissionOut
from app.storage import serve_file, upload_bytes
from app.tasks.grading_tasks import grade_submission
from app.tasks.ocr_tasks import ocr_submission

router = APIRouter(tags=["submissions"])
logger = logging.getLogger(__name__)

ALLOWED_TYPES = {"text", "image", "pdf"}
EXT_MAP = {"image": ".png", "pdf": ".pdf"}


def _validate_upload(content_type: str, data: bytes) -> None:
    if len(data) > settings.max_upload_bytes:
        limit_mb = settings.max_upload_bytes // (1024 * 1024)
        raise HTTPException(status_code=413, detail=f"上传文件不能超过 {limit_mb} MB")
    if content_type == "pdf":
        if not data.startswith(b"%PDF-"):
            raise HTTPException(status_code=400, detail="上传内容不是有效 PDF")
        return
    image_signatures = (
        data.startswith(b"\x89PNG\r\n\x1a\n"),
        data.startswith(b"\xff\xd8\xff"),
        data.startswith((b"GIF87a", b"GIF89a")),
        len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP",
    )
    if not any(image_signatures):
        raise HTTPException(status_code=400, detail="仅支持 PNG、JPEG、GIF 或 WebP 图片")


def _enqueue_or_mark_failed(db: Session, submission: Submission, task) -> None:
    """Broker 不可用时保留提交并明确标记失败，避免已落库却返回 500。"""
    try:
        task.delay(submission.id)
    except Retry:
        # Celery eager 测试会把 Worker 的重试信号同步抛回；不能误判为 Broker 故障。
        raise
    except Exception:
        logger.exception("提交 %s 的异步任务投递失败", submission.id)
        submission.status = SUBMISSION_STATUS_FAILED
        db.commit()


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
    if assignment.due_at is not None:
        due_at = assignment.due_at
        if due_at.tzinfo is None:
            due_at = due_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > due_at:
            raise HTTPException(status_code=409, detail="作业已截止，不能继续提交")

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
        has_confirmed = (
            db.query(GradingResult.id)
            .join(
                SubmissionAnswer,
                SubmissionAnswer.id == GradingResult.submission_answer_id,
            )
            .filter(
                SubmissionAnswer.submission_id == old.id,
                GradingResult.status == GRADING_STATUS_CONFIRMED,
            )
            .first()
            is not None
        )
        if old.status in (
            SUBMISSION_STATUS_TEACHER_REVIEWED,
            SUBMISSION_STATUS_COMPLETED,
        ) or has_confirmed:
            raise HTTPException(status_code=409, detail="教师已开始复核，不能覆盖提交")
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
        data = file.file.read(settings.max_upload_bytes + 1)
        if not data:
            raise HTTPException(status_code=400, detail="上传文件为空")
        _validate_upload(content_type, data)
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
        _enqueue_or_mark_failed(db, submission, ocr_submission)
    else:
        _enqueue_or_mark_failed(db, submission, grade_submission)

    return submission


@router.get("/storage/files/{path:path}")
def storage_file(
    path: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """仅提交者、所属作业教师和管理员可以读取学生作业文件。"""
    submission = db.query(Submission).filter(Submission.content_url == path).first()
    if submission is None:
        raise HTTPException(status_code=404, detail="文件不存在")
    if user.role == ROLE_STUDENT and submission.student_id != user.id:
        raise HTTPException(status_code=403, detail="无权查看该文件")
    if user.role == ROLE_TEACHER:
        assignment = db.get(Assignment, submission.assignment_id)
        if assignment is None or assignment.teacher_id != user.id:
            raise HTTPException(status_code=403, detail="无权查看该文件")
    if user.role not in (ROLE_ADMIN, ROLE_TEACHER, ROLE_STUDENT):
        raise HTTPException(status_code=403, detail="无权查看该文件")
    return serve_file(path)


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
