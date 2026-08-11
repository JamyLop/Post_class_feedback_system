from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.deps import require_roles
from app.core.database import get_db
from app.models.knowledge import KnowledgePoint
from app.models.user import ROLE_ADMIN, ROLE_TEACHER
from app.schemas.knowledge import (
    KnowledgePointCreate,
    KnowledgePointOut,
    KnowledgePointTreeNode,
)

router = APIRouter(prefix="/knowledge-points", tags=["knowledge-points"])

_manager = require_roles([ROLE_ADMIN, ROLE_TEACHER])


@router.post("", response_model=KnowledgePointOut)
def create_kp(
    body: KnowledgePointCreate,
    db: Session = Depends(get_db),
    user=Depends(_manager),
):
    if body.parent_id is not None and db.get(KnowledgePoint, body.parent_id) is None:
        raise HTTPException(status_code=400, detail="父知识点不存在")
    if db.query(KnowledgePoint).filter(KnowledgePoint.code == body.code).first():
        raise HTTPException(status_code=409, detail="知识点编码已存在")
    kp = KnowledgePoint(**body.model_dump())
    db.add(kp)
    db.commit()
    db.refresh(kp)
    return kp


@router.get("", response_model=list[KnowledgePointOut])
def list_kp(
    subject: str = Query(default="数学"),
    grade: str = Query(default="初中"),
    db: Session = Depends(get_db),
):
    return (
        db.query(KnowledgePoint)
        .filter(KnowledgePoint.subject == subject, KnowledgePoint.grade == grade)
        .order_by(KnowledgePoint.id.asc())
        .all()
    )


@router.get("/tree", response_model=list[KnowledgePointTreeNode])
def kp_tree(
    subject: str = Query(default="数学"),
    grade: str = Query(default="初中"),
    db: Session = Depends(get_db),
):
    nodes = (
        db.query(KnowledgePoint)
        .filter(KnowledgePoint.subject == subject, KnowledgePoint.grade == grade)
        .all()
    )
    by_id = {n.id: KnowledgePointTreeNode(id=n.id, name=n.name, code=n.code, chapter=n.chapter) for n in nodes}
    for n in nodes:
        node = by_id[n.id]
        if n.parent_id is not None and n.parent_id in by_id:
            by_id[n.parent_id].children.append(node)
    return [by_id[n.id] for n in nodes if n.parent_id is None or n.parent_id not in by_id]
