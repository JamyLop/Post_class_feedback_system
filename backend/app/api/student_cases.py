"""高三一生一案 API：总案、学科方案、目标任务、打卡、督查与版本。"""

from datetime import date, datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.class_ import Class, ClassStudent, ClassTeacher, StudentGuardian
from app.models.student_case import (
    CASE_STATUSES,
    CaseCycle,
    CaseGoal,
    CaseImportBatch,
    CaseImportDocument,
    CaseReview,
    CaseTask,
    CaseVersion,
    StudentCase,
    SubjectPlan,
    TaskCheckin,
)
from app.models.user import ROLE_ADMIN, ROLE_PARENT, ROLE_TEACHER, User
from app.schemas.student_case import (
    CaseCycleCreate,
    CaseCycleOut,
    CaseGoalCreate,
    CaseGoalOut,
    CaseImportBatchOut,
    CaseImportDocumentOut,
    CaseProgressOut,
    CaseReviewCreate,
    CaseReviewOut,
    CaseTaskCreate,
    CaseTaskOut,
    CaseVersionOut,
    StudentCaseCreate,
    StudentCaseDetail,
    StudentCaseOut,
    StudentCaseTransition,
    StudentCaseUpdate,
    SubjectPlanOut,
    SubjectPlanUpsert,
    TaskCheckinCreate,
    TaskCheckinOut,
)
from app.services.student_case_service import (
    PARENT_VISIBLE_STATUSES,
    audit,
    is_head_teacher,
    require_case_access,
    require_case_manager,
    teacher_subjects,
    transition_case,
    verify_case_membership,
)
from app.services.case_export import build_case_export_bytes

router = APIRouter(prefix="/student-cases", tags=["student-cases"])
_staff = require_roles([ROLE_ADMIN, ROLE_TEACHER])
_head_teacher = require_roles([ROLE_TEACHER])


def _detail(db: Session, case: StudentCase, user: User) -> dict:
    tasks = db.query(CaseTask).filter_by(student_case_id=case.id).order_by(CaseTask.due_on).all()
    task_ids = [task.id for task in tasks]
    return {
        **_case_out(db, case),
        "viewer_role": user.role,
        "can_manage": user.role == ROLE_TEACHER and is_head_teacher(db, case.class_id, user.id),
        "subject_plans": db.query(SubjectPlan).filter_by(student_case_id=case.id).order_by(SubjectPlan.id).all(),
        "goals": db.query(CaseGoal).filter_by(student_case_id=case.id).order_by(CaseGoal.id).all(),
        "tasks": tasks,
        "task_checkins": (
            db.query(TaskCheckin)
            .filter(TaskCheckin.task_id.in_(task_ids))
            .order_by(TaskCheckin.checked_in_at.desc())
            .all()
            if task_ids
            else []
        ),
        "reviews": db.query(CaseReview).filter_by(student_case_id=case.id).order_by(CaseReview.reviewed_at.desc()).all(),
    }


def _case_out(db: Session, case: StudentCase) -> dict:
    data = StudentCaseOut.model_validate(case).model_dump()
    student = db.get(User, case.student_id)
    cls = db.get(Class, case.class_id)
    data["student_name"] = student.name if student else None
    data["class_name"] = cls.name if cls else None
    return data


@router.post("/cycles", response_model=CaseCycleOut)
def create_cycle(
    body: CaseCycleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles([ROLE_ADMIN])),
):
    cycle = CaseCycle(**body.model_dump(), grade="高三")
    db.add(cycle)
    db.flush()
    audit(db, user.id, "cycle.create", "case_cycle", cycle.id)
    db.commit()
    db.refresh(cycle)
    return cycle


@router.get("/cycles", response_model=list[CaseCycleOut])
def list_cycles(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return db.query(CaseCycle).order_by(CaseCycle.starts_on.desc()).all()


@router.get("/children", response_model=list[StudentCaseOut])
def family_cases(
    cycle_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles([ROLE_PARENT])),
):
    student_ids = [
        row.student_id
        for row in db.query(StudentGuardian).filter_by(parent_id=user.id).all()
    ]
    query = db.query(StudentCase).filter(
        StudentCase.student_id.in_(student_ids),
        StudentCase.status.in_(PARENT_VISIBLE_STATUSES),
    )
    if cycle_id is not None:
        query = query.filter(StudentCase.cycle_id == cycle_id)
    return [_case_out(db, case) for case in query.order_by(StudentCase.updated_at.desc()).all()]


@router.get("/progress", response_model=CaseProgressOut)
def supervision_progress(
    class_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(_staff),
):
    query = db.query(StudentCase)
    if class_id is not None:
        if user.role == ROLE_TEACHER and not (
            is_head_teacher(db, class_id, user.id) or teacher_subjects(db, class_id, user.id)
        ):
            raise HTTPException(status_code=403, detail="无权查看该班级进展")
        query = query.filter(StudentCase.class_id == class_id)
    elif user.role == ROLE_TEACHER:
        legacy_ids = [row.id for row in db.query(Class).filter(Class.teacher_id == user.id)]
        relation_ids = [row.class_id for row in db.query(ClassTeacher).filter(ClassTeacher.teacher_id == user.id)]
        query = query.filter(StudentCase.class_id.in_(set(legacy_ids + relation_ids)))
    elif user.role != ROLE_ADMIN:
        # 学生不属于一生一案的内容管理或发布对象，保留其原作业系统权限即可。
        query = query.filter(StudentCase.id == -1)
    cases = query.all()
    ids = [row.id for row in cases]
    overdue = 0
    long_unreviewed = 0
    if ids:
        overdue = db.query(func.count(CaseTask.id)).filter(
            CaseTask.student_case_id.in_(ids),
            CaseTask.due_on < date.today(),
            CaseTask.status.notin_(["completed", "cancelled"]),
        ).scalar() or 0
        reviewed_case_ids = {
            row[0] for row in db.query(CaseReview.student_case_id).filter(
                CaseReview.student_case_id.in_(ids)
            ).distinct()
        }
        long_unreviewed = len(set(ids) - reviewed_case_ids)
    counts = {status: 0 for status in CASE_STATUSES}
    for row in cases:
        counts[row.status] += 1
    return {"total": len(cases), **counts, "overdue_tasks": overdue, "long_unreviewed": long_unreviewed}


@router.get("/import-batches", response_model=list[CaseImportBatchOut])
def list_import_batches(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles([ROLE_ADMIN])),
):
    return db.query(CaseImportBatch).order_by(CaseImportBatch.created_at.desc()).all()


@router.get(
    "/import-batches/{batch_id}/documents",
    response_model=list[CaseImportDocumentOut],
)
def list_import_documents(
    batch_id: int,
    document_status: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles([ROLE_ADMIN])),
):
    if db.get(CaseImportBatch, batch_id) is None:
        raise HTTPException(status_code=404, detail="导入批次不存在")
    query = db.query(CaseImportDocument).filter_by(batch_id=batch_id)
    if document_status:
        query = query.filter(CaseImportDocument.status == document_status)
    return query.order_by(
        CaseImportDocument.detected_student_name,
        CaseImportDocument.source_version,
    ).all()


@router.post("", response_model=StudentCaseOut)
def create_student_case(
    body: StudentCaseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_head_teacher),
):
    cycle = db.get(CaseCycle, body.cycle_id)
    if cycle is None or cycle.grade != "高三":
        raise HTTPException(status_code=404, detail="高三试点周期不存在")
    cls = db.get(Class, body.class_id)
    if cls is None or cls.grade != "高三":
        raise HTTPException(status_code=409, detail="第一版只能为高三班级建立总案")
    if not is_head_teacher(db, body.class_id, user.id):
        raise HTTPException(status_code=403, detail="仅班主任可建立学生总案")
    verify_case_membership(db, body.student_id, body.class_id)
    case = StudentCase(**body.model_dump())
    db.add(case)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="该学生在此周期已有总案") from exc
    audit(db, user.id, "case.create", "student_case", case.id, case.id)
    db.commit()
    db.refresh(case)
    return _case_out(db, case)


@router.get("", response_model=list[StudentCaseOut])
def list_student_cases(
    class_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(StudentCase)
    if user.role == ROLE_PARENT:
        student_ids = [
            row.student_id
            for row in db.query(StudentGuardian).filter_by(parent_id=user.id).all()
        ]
        query = query.filter(
            StudentCase.student_id.in_(student_ids),
            StudentCase.status.in_(PARENT_VISIBLE_STATUSES),
        )
    elif user.role == ROLE_TEACHER:
        legacy_ids = [row.id for row in db.query(Class).filter(Class.teacher_id == user.id)]
        relation_ids = [row.class_id for row in db.query(ClassTeacher).filter(ClassTeacher.teacher_id == user.id)]
        query = query.filter(StudentCase.class_id.in_(set(legacy_ids + relation_ids)))
    elif user.role != ROLE_ADMIN:
        query = query.filter(StudentCase.id == -1)
    if class_id is not None:
        query = query.filter(StudentCase.class_id == class_id)
    if status is not None:
        if status not in CASE_STATUSES:
            raise HTTPException(status_code=400, detail="未知总案状态")
        query = query.filter(StudentCase.status == status)
    return [_case_out(db, row) for row in query.order_by(StudentCase.updated_at.desc()).all()]


@router.get("/{case_id}", response_model=StudentCaseDetail)
def get_student_case(
    case_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    case = require_case_access(db, case_id, user)
    return _detail(db, case, user)


@router.get("/{case_id}/export")
def export_student_case(
    case_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # 导出权限与查看一致：家长仅可见已确认版本，班主任/管理员可见全部
    case = require_case_access(db, case_id, user)
    detail = _detail(db, case, user)
    student = db.get(User, case.student_id)
    cls = db.get(Class, case.class_id)
    cycle = db.get(CaseCycle, case.cycle_id)
    data = build_case_export_bytes(
        case=case,
        student_name=student.name if student else f"学生#{case.student_id}",
        class_name=cls.name if cls else f"班级#{case.class_id}",
        cycle_name=cycle.name if cycle else "",
        subject_plans=detail["subject_plans"],
        tasks=detail["tasks"],
        checkins=detail["task_checkins"],
        reviews=detail["reviews"],
        cycle=cycle,
    )
    audit(db, user.id, "case.export", "student_case", case.id, case.id, {"version": case.version, "status": case.status})
    db.commit()
    filename = f"{student.name if student else case.student_id}_一生一案_V{case.version}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.docx"
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}; filename=\"export.docx\"",
            "X-Case-Version": str(case.version),
            "X-Case-Status": case.status,
        },
    )


@router.patch("/{case_id}", response_model=StudentCaseOut)
def update_student_case(
    case_id: int,
    body: StudentCaseUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(_head_teacher),
):
    case = require_case_access(db, case_id, user, write=True)
    require_case_manager(db, case, user)
    changes = body.model_dump(exclude_none=True, exclude={"change_reason"})
    if case.status not in {"draft", "pending_confirmation"} and changes:
        # 执行中的正式内容不得无痕覆盖；调整前先走复盘状态机。
        raise HTTPException(status_code=409, detail="执行中的总案须先进入阶段复盘并生成新版本")
    for field, value in changes.items():
        setattr(case, field, value)
    audit(db, user.id, "case.update", "student_case", case.id, case.id, {"fields": list(changes)})
    db.commit()
    db.refresh(case)
    return _case_out(db, case)


@router.post("/{case_id}/transition", response_model=StudentCaseOut)
def change_case_status(
    case_id: int,
    body: StudentCaseTransition,
    db: Session = Depends(get_db),
    user: User = Depends(_head_teacher),
):
    case = require_case_access(db, case_id, user, write=True)
    require_case_manager(db, case, user)
    transition_case(db, case, body.target_status, user, body.reason)
    db.commit()
    db.refresh(case)
    return _case_out(db, case)


@router.get("/{case_id}/versions", response_model=list[CaseVersionOut])
def list_case_versions(
    case_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_case_access(db, case_id, user)
    return db.query(CaseVersion).filter_by(student_case_id=case_id).order_by(CaseVersion.version.desc()).all()


@router.put("/{case_id}/subject-plans/{subject}", response_model=SubjectPlanOut)
def upsert_subject_plan(
    case_id: int,
    subject: str,
    body: SubjectPlanUpsert,
    db: Session = Depends(get_db),
    user: User = Depends(_head_teacher),
):
    if body.subject != subject:
        raise HTTPException(status_code=400, detail="路径学科与请求内容不一致")
    case = require_case_access(db, case_id, user, write=True, subject=subject)
    require_case_manager(db, case, user)
    if case.status not in {"draft", "pending_confirmation", "adjusted"}:
        raise HTTPException(status_code=409, detail="当前状态不能修改学科方案")
    plan = db.query(SubjectPlan).filter_by(student_case_id=case_id, subject=subject).first()
    if plan is None:
        plan = SubjectPlan(student_case_id=case_id, **body.model_dump())
        db.add(plan)
    else:
        for field, value in body.model_dump().items():
            setattr(plan, field, value)
    db.flush()
    audit(db, user.id, "subject_plan.upsert", "subject_plan", plan.id, case.id, {"subject": subject})
    db.commit()
    db.refresh(plan)
    return plan


@router.post("/{case_id}/goals", response_model=CaseGoalOut)
def create_goal(
    case_id: int,
    body: CaseGoalCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_head_teacher),
):
    case = require_case_access(db, case_id, user, write=True, subject=body.subject)
    require_case_manager(db, case, user)
    goal = CaseGoal(student_case_id=case_id, **body.model_dump())
    db.add(goal)
    db.flush()
    audit(db, user.id, "goal.create", "case_goal", goal.id, case.id)
    db.commit()
    db.refresh(goal)
    return goal


@router.post("/{case_id}/tasks", response_model=CaseTaskOut)
def create_task(
    case_id: int,
    body: CaseTaskCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_head_teacher),
):
    case = require_case_access(db, case_id, user, write=True, subject=body.subject)
    require_case_manager(db, case, user)
    if case.status == "archived":
        raise HTTPException(status_code=409, detail="已归档方案不能新增任务")
    task = CaseTask(student_case_id=case_id, created_by=user.id, **body.model_dump())
    db.add(task)
    db.flush()
    audit(db, user.id, "task.create", "case_task", task.id, case.id)
    db.commit()
    db.refresh(task)
    return task


@router.put("/{case_id}/tasks/{task_id}", response_model=CaseTaskOut)
def update_task(
    case_id: int,
    task_id: int,
    body: CaseTaskCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_head_teacher),
):
    task = db.get(CaseTask, task_id)
    if task is None or task.student_case_id != case_id:
        raise HTTPException(status_code=404, detail="任务不存在")
    case = require_case_access(db, case_id, user, write=True, subject=body.subject)
    require_case_manager(db, case, user)
    if case.status == "archived":
        raise HTTPException(status_code=409, detail="已归档方案不能修改任务")
    for field, value in body.model_dump().items():
        setattr(task, field, value)
    audit(db, user.id, "task.update", "case_task", task.id, case.id)
    db.commit()
    db.refresh(task)
    return task


@router.post("/tasks/{task_id}/checkins", response_model=TaskCheckinOut)
def checkin_task(
    task_id: int,
    body: TaskCheckinCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_head_teacher),
):
    task = db.get(CaseTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    case = require_case_access(db, task.student_case_id, user, write=True, subject=task.subject)
    require_case_manager(db, case, user)
    # 执行记录由班主任代为确认录入，student_id 始终指向记录所属学生。
    checkin = TaskCheckin(task_id=task.id, student_id=case.student_id, **body.model_dump())
    db.add(checkin)
    if body.completion_rate == 100:
        task.status = "completed"
    elif body.completion_rate > 0:
        task.status = "in_progress"
    db.flush()
    audit(db, user.id, "task.checkin", "task_checkin", checkin.id, case.id, {"rate": body.completion_rate})
    db.commit()
    db.refresh(checkin)
    return checkin


@router.post("/{case_id}/reviews", response_model=CaseReviewOut)
def create_review(
    case_id: int,
    body: CaseReviewCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_staff),
):
    case = require_case_access(db, case_id, user, write=False, subject=body.subject)
    if body.review_level in {"school", "principal"} and user.role != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="校级/校长督查仅管理员可提交")
    if body.review_level not in {"school", "principal"}:
        require_case_manager(db, case, user)
    review = CaseReview(student_case_id=case_id, reviewer_id=user.id, **body.model_dump())
    db.add(review)
    db.flush()
    audit(db, user.id, "review.create", "case_review", review.id, case.id, {"level": body.review_level})
    db.commit()
    db.refresh(review)
    return review
