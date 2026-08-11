from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.deps import require_roles
from app.core.database import get_db
from app.models.knowledge import KnowledgePoint
from app.models.question import Question, QuestionKnowledgePoint
from app.models.user import ROLE_ADMIN, ROLE_TEACHER
from app.schemas.question import (
    QuestionCreate,
    QuestionDetail,
    QuestionOut,
    QuestionUpdate,
)

router = APIRouter(prefix="/questions", tags=["questions"])

_manager = require_roles([ROLE_ADMIN, ROLE_TEACHER])


@router.post("", response_model=QuestionDetail)
def create_question(
    body: QuestionCreate,
    db: Session = Depends(get_db),
    user=Depends(_manager),
):
    question = Question(
        subject=body.subject,
        grade=body.grade,
        question_type=body.question_type,
        content=body.content,
        standard_answer=body.standard_answer,
        score=body.score,
        difficulty=body.difficulty,
        grading_rule=body.grading_rule,
    )
    db.add(question)
    db.flush()
    for ref in body.knowledge_points:
        if db.get(KnowledgePoint, ref.id) is None:
            raise HTTPException(status_code=400, detail=f"知识点 {ref.id} 不存在")
        db.add(
            QuestionKnowledgePoint(
                question_id=question.id,
                knowledge_point_id=ref.id,
                weight=ref.weight,
            )
        )
    db.commit()
    db.refresh(question)
    return question


@router.get("", response_model=list[QuestionOut])
def list_questions(
    question_type: str | None = Query(default=None),
    keyword: str = Query(default="", max_length=64),
    db: Session = Depends(get_db),
):
    q = db.query(Question)
    if question_type:
        q = q.filter(Question.question_type == question_type)
    if keyword:
        q = q.filter(Question.content.ilike(f"%{keyword}%"))
    return q.order_by(Question.id.desc()).limit(200).all()


@router.get("/{question_id}", response_model=QuestionDetail)
def get_question(question_id: int, db: Session = Depends(get_db)):
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="题目不存在")
    return question


@router.put("/{question_id}", response_model=QuestionDetail)
def update_question(
    question_id: int,
    body: QuestionUpdate,
    db: Session = Depends(get_db),
    user=Depends(_manager),
):
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="题目不存在")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(question, k, v)
    db.commit()
    db.refresh(question)
    return question
