"""调班的预览、提交和历史均仅限德育主任/管理员。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.auth.deps import require_roles
from app.core.database import get_db
from app.models.class_transfer import ClassTransferBatch
from app.models.user import User, ROLE_ADMIN, ROLE_DEYU_DIRECTOR
from app.schemas.class_transfer import TransferPreviewIn, TransferCommitIn
from app.services.class_transfer_service import build_preview, commit_transfer, batch_out

router = APIRouter(prefix="/class-transfers", tags=["class-transfers"])
manager = require_roles([ROLE_ADMIN, ROLE_DEYU_DIRECTOR])


@router.post("/preview")
def preview(body: TransferPreviewIn, db: Session = Depends(get_db), user: User = Depends(manager)):
    return build_preview(db, body)[0]


@router.post("")
def commit(body: TransferCommitIn, db: Session = Depends(get_db), user: User = Depends(manager)):
    try:
        return commit_transfer(db, body, user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "提交编号或班级关系发生冲突，请查看记录并重新预览") from exc


@router.get("")
def history(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
            db: Session = Depends(get_db), user: User = Depends(manager)):
    query = db.query(ClassTransferBatch)
    return dict(total=query.count(), items=[batch_out(db, b) for b in query.order_by(
        ClassTransferBatch.id.desc()).offset(offset).limit(limit)])
