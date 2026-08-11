from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.assignment import (
    ASSIGNMENT_STATUS_DRAFT,
    ASSIGNMENT_STATUS_PUBLISHED,
    Assignment,
    AssignmentQuestion,
)
from app.models.class_ import Class, ClassStudent
from app.models.question import Question
from app.models.user import ROLE_ADMIN, ROLE_STUDENT, ROLE_TEACHER, User
from app.schemas.assignment import (
    AssignmentAddQuestions,
    AssignmentCreate,
    AssignmentDetail,
    AssignmentQuestionOut,
    AssignmentUpdate,
)

router = APIRouter(prefix="/assignments", tags=["assignments"])

_manager = require_roles([ROLE_ADMIN, ROLE_TEACHER])


def _get_assignment(db: Session, assignment_id: int) -> Assignment:
    a = db.get(Assignment, assignment_id)
    if a is None:
        raise HTTPException(status_code=404, detail="作业不存在")
    return a


def _check_teacher_owns(db: Session, assignment: Assignment, user: User) -> None:
    if user.role == ROLE_ADMIN:
        return
    if assignment.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="无权操作该作业")


@router.post("", response_model=AssignmentDetail)
def create_assignment(
    body: AssignmentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_manager),
):
    cls = db.get(Class, body.class_id)
    if cls is None:
        raise HTTPException(status_code=404, detail="班级不存在")
    if user.role != ROLE_ADMIN and cls.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="无权在该班级布置作业")
    a = Assignment(
        class_id=body.class_id,
        teacher_id=user.id,
        title=body.title,
        subject=body.subject,
        description=body.description,
        due_at=body.due_at,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


@router.get("", response_model=list[AssignmentDetail])
def list_assignments(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(Assignment)
    if user.role == ROLE_TEACHER:
        q = q.filter(Assignment.teacher_id == user.id)
    elif user.role == ROLE_STUDENT:
        class_ids = [
            cs.class_id
            for cs in db.query(ClassStudent)
            .filter(ClassStudent.student_id == user.id)
            .all()
        ]
        q = q.filter(
            Assignment.class_id.in_(class_ids),
            Assignment.status.in_([ASSIGNMENT_STATUS_PUBLISHED]),
        )
    rows = q.order_by(Assignment.id.desc()).all()
    return [_to_detail(db, a) for a in rows]


@router.get("/{assignment_id}", response_model=AssignmentDetail)
def get_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    a = _get_assignment(db, assignment_id)
    if user.role == ROLE_STUDENT:
        member = (
            db.query(ClassStudent)
            .filter(
                ClassStudent.class_id == a.class_id,
                ClassStudent.student_id == user.id,
            )
            .first()
        )
        if member is None:
            raise HTTPException(status_code=403, detail="无权查看该作业")
    return _to_detail(db, a)


@router.put("/{assignment_id}", response_model=AssignmentDetail)
def update_assignment(
    assignment_id: int,
    body: AssignmentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(_manager),
):
    a = _get_assignment(db, assignment_id)
    _check_teacher_owns(db, a, user)
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(a, k, v)
    db.commit()
    db.refresh(a)
    return _to_detail(db, a)


@router.post("/{assignment_id}/publish", response_model=AssignmentDetail)
def publish_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(_manager),
):
    a = _get_assignment(db, assignment_id)
    _check_teacher_owns(db, a, user)
    if not a.questions:
        raise HTTPException(status_code=400, detail="作业还没有题目，无法发布")
    a.status = ASSIGNMENT_STATUS_PUBLISHED
    db.commit()
    db.refresh(a)
    return _to_detail(db, a)


@router.post("/{assignment_id}/questions", response_model=AssignmentDetail)
def add_questions(
    assignment_id: int,
    body: AssignmentAddQuestions,
    db: Session = Depends(get_db),
    user: User = Depends(_manager),
):
    a = _get_assignment(db, assignment_id)
    _check_teacher_owns(db, a, user)
    existing = {
        aq.question_id for aq in a.questions
    }
    order = max((aq.question_order for aq in a.questions), default=-1) + 1
    for qid in body.question_ids:
        if qid in existing:
            continue
        if db.get(Question, qid) is None:
            raise HTTPException(status_code=400, detail=f"题目 {qid} 不存在")
        db.add(
            AssignmentQuestion(
                assignment_id=a.id, question_id=qid, question_order=order
            )
        )
        order += 1
    db.commit()
    db.refresh(a)
    return _to_detail(db, a)


@router.get("/{assignment_id}/questions", response_model=list[AssignmentQuestionOut])
def list_assignment_questions(
    assignment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    a = _get_assignment(db, assignment_id)
    if user.role == ROLE_STUDENT:
        member = (
            db.query(ClassStudent)
            .filter(
                ClassStudent.class_id == a.class_id,
                ClassStudent.student_id == user.id,
            )
            .first()
        )
        if member is None:
            raise HTTPException(status_code=403, detail="无权查看该作业")
    return [
        AssignmentQuestionOut(
            id=q.question_id,
            question_order=q.question_order,
            question_type=q_question.question_type,
            content=q_question.content,
            score=q_question.score,
            standard_answer=q_question.standard_answer,
        )
        for q in sorted(a.questions, key=lambda x: x.question_order)
        for q_question in [db.get(Question, q.question_id)]
    ]


def _to_detail(db: Session, a: Assignment) -> AssignmentDetail:
    questions = []
    for aq in sorted(a.questions, key=lambda x: x.question_order):
        q = db.get(Question, aq.question_id)
        if q is None:
            continue
        questions.append(
            AssignmentQuestionOut(
                id=q.id,
                question_order=aq.question_order,
                question_type=q.question_type,
                content=q.content,
                score=q.score,
                standard_answer=q.standard_answer,
            )
        )
    return AssignmentDetail(
        id=a.id,
        class_id=a.class_id,
        teacher_id=a.teacher_id,
        title=a.title,
        subject=a.subject,
        description=a.description,
        due_at=a.due_at,
        status=a.status,
        questions=questions,
    )
