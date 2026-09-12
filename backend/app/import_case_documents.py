"""执行首批5名高三学生历史DOCX试导入。用法：python -m app.import_case_documents"""

from pathlib import Path

from app.core.database import SessionLocal
from app.models.user import ROLE_ADMIN, User
from app.services.document_import_service import run_pilot_import

PILOT_FOLDERS = [
    "高三侯思伊",
    "高三唐俊翔",
    "高三张俊超",
    "高三张筠舒",
    "高三徐援伟",
]


def main() -> None:
    db = SessionLocal()
    try:
        actor = db.query(User).filter(User.role == ROLE_ADMIN).order_by(User.id).first()
        if actor is None:
            raise RuntimeError("数据库中没有管理员账号")
        source_root = Path(__file__).resolve().parents[2] / "docx" / "一生一案"
        batch = run_pilot_import(
            db,
            actor,
            source_root,
            PILOT_FOLDERS,
            batch_key="g3-pilot-20260827-v1",
        )
        print({"batch_id": batch.id, "status": batch.status, **batch.summary})
    finally:
        db.close()


if __name__ == "__main__":
    main()
