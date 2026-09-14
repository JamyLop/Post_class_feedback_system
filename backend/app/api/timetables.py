"""课表 API：德育主任统一排课，教师只读取自己的安排。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.class_ import Class, ClassTeacher
from app.models.timetable import TimetableEntry
from app.models.user import ROLE_ADMIN, ROLE_DEYU_DIRECTOR, ROLE_SUBJECT_TEACHER, ROLE_TEACHER, User
from app.schemas.timetable import TimetableEntryCreate, TimetableEntryOut, TimetableEntryUpdate

router = APIRouter(prefix="/timetables", tags=["timetables"])
_scheduler = require_roles([ROLE_ADMIN, ROLE_DEYU_DIRECTOR])
_teacher_roles = (ROLE_TEACHER, ROLE_SUBJECT_TEACHER)


def _out(db: Session, rows: list[TimetableEntry]) -> list[dict]:
    class_names = {item.id: item.name for item in db.query(Class).filter(Class.id.in_({r.class_id for r in rows})).all()} if rows else {}
    teacher_names = {item.id: item.name for item in db.query(User).filter(User.id.in_({r.teacher_id for r in rows})).all()} if rows else {}
    return [
        {**TimetableEntryOut.model_validate(row).model_dump(exclude={"class_name", "teacher_name"}),
         "class_name": class_names.get(row.class_id, ""), "teacher_name": teacher_names.get(row.teacher_id, "")}
        for row in rows
    ]


def _validate_assignment(db: Session, class_id: int, teacher_id: int) -> None:
    cls = db.get(Class, class_id)
    teacher = db.get(User, teacher_id)
    if cls is None:
        raise HTTPException(status_code=404, detail="班级不存在")
    if teacher is None or teacher.role not in _teacher_roles:
        raise HTTPException(status_code=422, detail="请选择班主任或任课老师")
    # 排课必须落在既有教学关系内，避免把课程误排给无关教师。
    is_assigned = cls.teacher_id == teacher_id or db.query(ClassTeacher.id).filter_by(class_id=class_id, teacher_id=teacher_id).first()
    if not is_assigned:
        raise HTTPException(status_code=422, detail="该教师未分配到此班级，请先维护任课关系")


def _save(db: Session, entry: TimetableEntry) -> TimetableEntry:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="该班级或教师在此星期和节次已有课程") from exc
    db.refresh(entry)
    return entry


@router.get("", response_model=list[TimetableEntryOut])
def list_timetable(
    class_id: int | None = Query(default=None),
    teacher_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(TimetableEntry)
    if user.role in _teacher_roles:
        query = query.filter(TimetableEntry.teacher_id == user.id)
    elif user.role not in (ROLE_ADMIN, ROLE_DEYU_DIRECTOR):
        raise HTTPException(status_code=403, detail="无权查看课表")
    if class_id is not None:
        query = query.filter(TimetableEntry.class_id == class_id)
    if teacher_id is not None and user.role in (ROLE_ADMIN, ROLE_DEYU_DIRECTOR):
        query = query.filter(TimetableEntry.teacher_id == teacher_id)
    return _out(db, query.order_by(TimetableEntry.weekday, TimetableEntry.period, TimetableEntry.id).all())


@router.get("/mine", response_model=list[TimetableEntryOut])
def my_timetable(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role not in _teacher_roles:
        raise HTTPException(status_code=403, detail="仅教师可查看个人课表")
    rows = db.query(TimetableEntry).filter_by(teacher_id=user.id).order_by(TimetableEntry.weekday, TimetableEntry.period).all()
    return _out(db, rows)


@router.post("", response_model=TimetableEntryOut)
def create_timetable_entry(body: TimetableEntryCreate, db: Session = Depends(get_db), user: User = Depends(_scheduler)):
    _validate_assignment(db, body.class_id, body.teacher_id)
    entry = TimetableEntry(**body.model_dump(), subject=body.subject.strip(), classroom=body.classroom.strip())
    db.add(entry)
    return _out(db, [_save(db, entry)])[0]


@router.put("/{entry_id}", response_model=TimetableEntryOut)
def update_timetable_entry(entry_id: int, body: TimetableEntryUpdate, db: Session = Depends(get_db), user: User = Depends(_scheduler)):
    entry = db.get(TimetableEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="课程不存在")
    changes = body.model_dump(exclude_unset=True)
    class_id, teacher_id = changes.get("class_id", entry.class_id), changes.get("teacher_id", entry.teacher_id)
    _validate_assignment(db, class_id, teacher_id)
    for field, value in changes.items():
        setattr(entry, field, value.strip() if field in ("subject", "classroom") else value)
    return _out(db, [_save(db, entry)])[0]


@router.delete("/{entry_id}")
def delete_timetable_entry(entry_id: int, db: Session = Depends(get_db), user: User = Depends(_scheduler)):
    entry = db.get(TimetableEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="课程不存在")
    db.delete(entry)
    db.commit()
    return {"ok": True}
