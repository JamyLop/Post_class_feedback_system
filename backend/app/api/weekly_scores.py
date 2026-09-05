"""周测成绩 API：单条录入、批量录入、查询、修改、删除与趋势。"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.class_ import Class, ClassStudent, ClassTeacher, StudentGuardian
from app.models.user import ROLE_ADMIN, ROLE_PARENT, ROLE_STUDENT, ROLE_SUBJECT_TEACHER, ROLE_TEACHER, User
from app.models.weekly_score import WeeklyTestScore, WeeklyScoreEvaluation
from app.schemas.weekly_score import (
    ClassWeeklySummary,
    WeeklyScoreEvaluationSave,
    WeeklyTestScoreBatchCreate,
    WeeklyTestScoreCreate,
    WeeklyTestScoreOut,
    WeeklyTestScoreUpdate,
    WeeklyTestTrendPoint,
)

router = APIRouter(prefix="/weekly-test-scores", tags=["weekly-test-scores"])


def _enrich(row: WeeklyTestScore, db: Session, user: User) -> dict:
    data = WeeklyTestScoreOut.model_validate(row).model_dump()
    stu = db.get(User, row.student_id)
    cls = db.get(Class, row.class_id)
    data["student_name"] = stu.name if stu else None
    data["class_name"] = cls.name if cls else None
    data["can_evaluate"] = _evaluation_role(db, row, user) is not None
    return data


def _evaluation_role(db: Session, row: WeeklyTestScore, user: User) -> str | None:
    if user.role not in (ROLE_TEACHER, ROLE_SUBJECT_TEACHER):
        return None
    cls = db.get(Class, row.class_id)
    relations = db.query(ClassTeacher).filter_by(class_id=row.class_id, teacher_id=user.id).all()
    if cls and (cls.teacher_id == user.id or any(r.role == "head_teacher" for r in relations)):
        return "head_teacher"
    if any(r.role == "subject_teacher" and r.subject == row.subject for r in relations):
        return "subject_teacher"
    return None


def _can_manage_class(db: Session, class_id: int, user: User) -> bool:
    if user.role == ROLE_ADMIN:
        return True
    if user.role != ROLE_TEACHER:
        return False
    cls = db.get(Class, class_id)
    if cls is None:
        return False
    if cls.teacher_id == user.id:
        return True
    return db.query(ClassTeacher).filter_by(class_id=class_id, teacher_id=user.id).first() is not None


def _check_can_write(db: Session, class_id: int, user: User):
    if not _can_manage_class(db, class_id, user):
        raise HTTPException(status_code=403, detail="无权录入该班级周测成绩")


def _verify_membership(db: Session, student_id: int, class_id: int):
    if db.query(ClassStudent).filter_by(class_id=class_id, student_id=student_id).first() is None:
        raise HTTPException(status_code=409, detail="学生不属于该班级")


def _filter_scope(query, db: Session, user: User):
    if user.role == ROLE_ADMIN:
        return query
    if user.role == ROLE_SUBJECT_TEACHER:
        # 任课账号仅能读取自己任教班级的对应学科，所有周测读取接口共用此边界。
        relations = db.query(ClassTeacher).filter_by(teacher_id=user.id).all()
        scopes = [and_(WeeklyTestScore.class_id == r.class_id, WeeklyTestScore.subject == r.subject)
                  for r in relations if r.role == "subject_teacher" and r.subject]
        head_ids = [r.id for r in db.query(Class).filter_by(teacher_id=user.id).all()]
        head_ids += [r.class_id for r in relations if r.role == "head_teacher"]
        if head_ids:
            scopes.append(WeeklyTestScore.class_id.in_(head_ids))
        return query.filter(or_(*scopes)) if scopes else query.filter(WeeklyTestScore.id == -1)
    if user.role == ROLE_TEACHER:
        # 教师仅可见自己负责的班级
        legacy_ids = [r.id for r in db.query(Class).filter(Class.teacher_id == user.id).all()]
        rel_ids = [r.class_id for r in db.query(ClassTeacher).filter(ClassTeacher.teacher_id == user.id).all()]
        allowed = set(legacy_ids + rel_ids)
        if not allowed:
            return query.filter(WeeklyTestScore.id == -1)
        return query.filter(WeeklyTestScore.class_id.in_(allowed))
    if user.role == ROLE_STUDENT:
        return query.filter(WeeklyTestScore.student_id == user.id)
    if user.role == ROLE_PARENT:
        student_ids = [r.student_id for r in db.query(StudentGuardian).filter_by(parent_id=user.id).all()]
        if not student_ids:
            return query.filter(WeeklyTestScore.id == -1)
        return query.filter(WeeklyTestScore.student_id.in_(student_ids))
    return query.filter(WeeklyTestScore.id == -1)


@router.get("", response_model=list[WeeklyTestScoreOut])
def list_scores(
    class_id: int | None = Query(default=None),
    student_id: int | None = Query(default=None),
    subject: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(WeeklyTestScore)
    q = _filter_scope(q, db, user)
    if class_id is not None:
        q = q.filter(WeeklyTestScore.class_id == class_id)
    if student_id is not None:
        q = q.filter(WeeklyTestScore.student_id == student_id)
    if subject:
        q = q.filter(WeeklyTestScore.subject == subject)
    if start_date:
        q = q.filter(WeeklyTestScore.exam_date >= start_date)
    if end_date:
        q = q.filter(WeeklyTestScore.exam_date <= end_date)
    rows = q.order_by(WeeklyTestScore.exam_date.desc(), WeeklyTestScore.id.desc()).all()
    return [_enrich(r, db, user) for r in rows]


@router.get("/trend", response_model=list[WeeklyTestTrendPoint])
def trend(
    student_id: int = Query(...),
    subject: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(WeeklyTestScore).filter(WeeklyTestScore.student_id == student_id)
    q = _filter_scope(q, db, user)
    if subject:
        q = q.filter(WeeklyTestScore.subject == subject)
    rows = q.order_by(WeeklyTestScore.exam_date.asc()).all()
    return [WeeklyTestTrendPoint(exam_date=r.exam_date, exam_name=r.exam_name, score=r.score, max_score=r.max_score) for r in rows]


@router.get("/class-summary", response_model=list[ClassWeeklySummary])
def class_summary(
    class_id: int = Query(...),
    subject: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(WeeklyTestScore).filter(WeeklyTestScore.class_id == class_id)
    q = _filter_scope(q, db, user)
    if subject:
        q = q.filter(WeeklyTestScore.subject == subject)
    # 按 (exam_date, subject, exam_name) 分组统计
    rows = (
        q.with_entities(
            WeeklyTestScore.exam_date,
            WeeklyTestScore.exam_name,
            WeeklyTestScore.subject,
            func.avg(WeeklyTestScore.score),
            func.max(WeeklyTestScore.score),
            func.min(WeeklyTestScore.score),
            func.count(WeeklyTestScore.id),
        )
        .group_by(WeeklyTestScore.exam_date, WeeklyTestScore.exam_name, WeeklyTestScore.subject)
        .order_by(WeeklyTestScore.exam_date.desc())
        .all()
    )
    return [
        ClassWeeklySummary(
            exam_date=r[0], exam_name=r[1], subject=r[2],
            avg_score=round(float(r[3] or 0), 2), max_score=float(r[4] or 0),
            min_score=float(r[5] or 0), count=int(r[6]),
        )
        for r in rows
    ]


@router.post("", response_model=WeeklyTestScoreOut)
def create_score(
    body: WeeklyTestScoreCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles([ROLE_ADMIN, ROLE_TEACHER])),
):
    _check_can_write(db, body.class_id, user)
    _verify_membership(db, body.student_id, body.class_id)
    if body.score > body.max_score:
        raise HTTPException(status_code=400, detail="得分不能超过满分")
    row = WeeklyTestScore(**body.model_dump(), recorded_by=user.id)
    db.add(row)
    try:
        db.commit()
        db.refresh(row)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="该学生该科目当日已有成绩，请编辑而非重复录入") from exc
    return _enrich(row, db, user)


@router.post("/batch", response_model=list[WeeklyTestScoreOut])
def batch_upsert(
    body: WeeklyTestScoreBatchCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles([ROLE_ADMIN, ROLE_TEACHER])),
):
    _check_can_write(db, body.class_id, user)
    if not body.records:
        raise HTTPException(status_code=400, detail="批量记录不能为空")
    results: list[WeeklyTestScore] = []
    for item in body.records:
        student_id = item.get("student_id")
        score = item.get("score")
        if student_id is None or score is None:
            raise HTTPException(status_code=400, detail="每条记录需包含 student_id 和 score")
        _verify_membership(db, int(student_id), body.class_id)
        try:
            score_val = float(score)
        except Exception:
            raise HTTPException(status_code=400, detail=f"学生 {student_id} 分数格式错误")
        max_score = float(item.get("max_score", body.max_score))
        if score_val > max_score:
            raise HTTPException(status_code=400, detail=f"学生 {student_id} 得分不能超过满分")
        rank = item.get("rank_in_class")
        remark = item.get("remark", "")
        existing = db.query(WeeklyTestScore).filter_by(
            class_id=body.class_id, student_id=student_id, subject=body.subject, exam_date=body.exam_date
        ).first()
        if existing:
            existing.score = score_val
            existing.max_score = max_score
            existing.rank_in_class = rank
            existing.remark = remark or ""
            existing.exam_name = body.exam_name or existing.exam_name
            existing.recorded_by = user.id
            results.append(existing)
        else:
            row = WeeklyTestScore(
                class_id=body.class_id, student_id=student_id, subject=body.subject,
                exam_date=body.exam_date, exam_name=body.exam_name, score=score_val,
                max_score=max_score, rank_in_class=rank, remark=remark or "", recorded_by=user.id
            )
            db.add(row)
            results.append(row)
    try:
        db.commit()
        for r in results:
            db.refresh(r)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="批量保存冲突") from exc
    return [_enrich(r, db, user) for r in results]


@router.put("/{score_id}", response_model=WeeklyTestScoreOut)
def update_score(
    score_id: int,
    body: WeeklyTestScoreUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles([ROLE_ADMIN, ROLE_TEACHER])),
):
    row = db.get(WeeklyTestScore, score_id)
    if row is None:
        raise HTTPException(status_code=404, detail="成绩记录不存在")
    _check_can_write(db, row.class_id, user)
    changes = body.model_dump(exclude_none=True)
    if "score" in changes or "max_score" in changes:
        new_score = changes.get("score", row.score)
        new_max = changes.get("max_score", row.max_score)
        if new_score > new_max:
            raise HTTPException(status_code=400, detail="得分不能超过满分")
    for k, v in changes.items():
        setattr(row, k, v)
    row.recorded_by = user.id
    try:
        db.commit()
        db.refresh(row)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="修改后与其他记录冲突") from exc
    return _enrich(row, db, user)


@router.put("/{score_id}/evaluation", response_model=WeeklyTestScoreOut)
def save_evaluation(
    score_id: int,
    body: WeeklyScoreEvaluationSave,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles([ROLE_TEACHER, ROLE_SUBJECT_TEACHER])),
):
    # 同一成绩串行保存，避免重复点击或并发请求创建同一教师的重复评价。
    row = db.query(WeeklyTestScore).filter_by(id=score_id).with_for_update().first()
    if row is None:
        raise HTTPException(status_code=404, detail="成绩记录不存在")
    role = _evaluation_role(db, row, user)
    if role is None:
        raise HTTPException(status_code=403, detail="仅本班班主任和对应学科老师可评价")
    evaluation = db.query(WeeklyScoreEvaluation).filter_by(score_id=row.id, teacher_id=user.id).first()
    if evaluation is None:
        evaluation = WeeklyScoreEvaluation(score_id=row.id, teacher_id=user.id)
        db.add(evaluation)
    evaluation.teacher_name = user.name
    evaluation.teacher_role = role
    evaluation.content = body.content
    db.commit()
    db.refresh(row)
    return _enrich(row, db, user)


@router.delete("/{score_id}")
def delete_score(
    score_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles([ROLE_ADMIN, ROLE_TEACHER])),
):
    row = db.get(WeeklyTestScore, score_id)
    if row is None:
        raise HTTPException(status_code=404, detail="成绩记录不存在")
    _check_can_write(db, row.class_id, user)
    db.delete(row)
    db.commit()
    return {"ok": True}
