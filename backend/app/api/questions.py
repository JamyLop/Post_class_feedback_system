from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.ai.question_parse import parse_questions
from app.auth.deps import require_roles
from app.core.config import settings
from app.core.database import get_db
from app.models.knowledge import KnowledgePoint
from app.models.question import Question, QuestionKnowledgePoint
from app.models.user import ROLE_ADMIN, ROLE_TEACHER
from app.ocr.provider import get_ocr_provider
from app.schemas.question import (
    QuestionBatchCreate,
    QuestionCreate,
    QuestionDetail,
    QuestionOut,
    QuestionParseOut,
    QuestionUpdate,
)

router = APIRouter(prefix="/questions", tags=["questions"])

_manager = require_roles([ROLE_ADMIN, ROLE_TEACHER])


def _to_detail(db: Session, question: Question) -> QuestionDetail:
    kp_list = []
    for qkp in question.knowledge_points:
        kp = db.get(KnowledgePoint, qkp.knowledge_point_id)
        kp_list.append(
            {
                "knowledge_point_id": qkp.knowledge_point_id,
                "name": kp.name if kp else "",
                "weight": qkp.weight,
            }
        )
    return QuestionDetail(
        id=question.id,
        subject=question.subject,
        grade=question.grade,
        question_type=question.question_type,
        content=question.content,
        standard_answer=question.standard_answer,
        score=question.score,
        difficulty=question.difficulty,
        grading_rule=question.grading_rule,
        knowledge_points=kp_list,
    )


def _create_one(db: Session, body: QuestionCreate) -> Question:
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
    return question


@router.post("/parse", response_model=list[QuestionParseOut])
def parse_questions_from_upload(
    content_text: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    user=Depends(_manager),
):
    """上传题目图片或粘贴题目文字，AI 解析出结构化题目列表（不入库）。"""
    raw_text = ""
    if file is not None:
        data = file.file.read(settings.max_upload_bytes + 1)
        if not data:
            raise HTTPException(status_code=400, detail="上传文件为空")
        result = get_ocr_provider().extract(data, "image")
        raw_text = result.raw_text
    elif content_text and content_text.strip():
        raw_text = content_text.strip()
    else:
        raise HTTPException(status_code=400, detail="请上传题目图片或输入题目文字")
    if not (raw_text or "").strip():
        raise HTTPException(status_code=400, detail="未能从输入中识别出文字内容")
    try:
        questions = parse_questions(raw_text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return questions


@router.post("/batch", response_model=list[QuestionDetail])
def batch_create_questions(
    body: QuestionBatchCreate,
    db: Session = Depends(get_db),
    user=Depends(_manager),
):
    """将 AI 解析确认后的题目批量入库。"""
    created = []
    for item in body.questions:
        created.append(_create_one(db, item))
    db.commit()
    for q in created:
        db.refresh(q)
    return [_to_detail(db, q) for q in created]


@router.post("", response_model=QuestionDetail)
def create_question(
    body: QuestionCreate,
    db: Session = Depends(get_db),
    user=Depends(_manager),
):
    question = _create_one(db, body)
    db.commit()
    db.refresh(question)
    return _to_detail(db, question)


@router.get("", response_model=list[QuestionOut], dependencies=[Depends(_manager)])
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


@router.get("/{question_id}", response_model=QuestionDetail, dependencies=[Depends(_manager)])
def get_question(question_id: int, db: Session = Depends(get_db)):
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="题目不存在")
    return _to_detail(db, question)


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
    return _to_detail(db, question)
