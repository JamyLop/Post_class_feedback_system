"""高三一生一案 API：总案、学科方案、目标任务、打卡、督查与版本。"""

from datetime import date, datetime, timezone
from urllib.parse import quote

import re

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_roles
from app.core.database import get_db
from app.core.security import hash_password
from app.models.class_ import Class, ClassStudent, ClassTeacher, StudentGuardian
from app.models.student_case import (
    CASE_STATUSES,
    CASE_STATUS_PENDING_CONFIRMATION,
    CASE_STATUS_REVISION_REQUIRED,
    CaseCycle,
    CaseGoal,
    CaseImportBatch,
    CaseImportDocument,
    CaseReview,
    CaseStudentProfile,
    CaseTask,
    CaseVersion,
    StudentCase,
    SubjectPlan,
    TaskCheckin,
)
from app.models.user import ROLE_ADMIN, ROLE_DEYU_DIRECTOR, ROLE_PARENT, ROLE_TEACHER, User
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
    DeyuReviewDecision,
    CaseStudentProfileOut,
    CaseStudentProfileUpsert,
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
# 校长 + 德育主任 + 班主任均可查看督查进度；仅班主任可写
_staff = require_roles([ROLE_ADMIN, ROLE_DEYU_DIRECTOR, ROLE_TEACHER])
_head_teacher = require_roles([ROLE_TEACHER])
_deyu_director = require_roles([ROLE_DEYU_DIRECTOR])


def _mask_health_for_viewer(profile_data: dict, viewer_role: str) -> dict:
    """若体检史设为不展示且查看者非校长(admin)，则隐藏具体内容。德育主任同班主任一样不可见。"""
    if profile_data.get("health_visible") is False and viewer_role != ROLE_ADMIN:
        masked = dict(profile_data)
        masked["allergy_history"] = ""
        masked["underlying_conditions"] = ""
        masked["other_health_notes"] = ""
        return masked
    return profile_data


def _detail(db: Session, case: StudentCase, user: User) -> dict:
    tasks = db.query(CaseTask).filter_by(student_case_id=case.id).order_by(CaseTask.due_on).all()
    task_ids = [task.id for task in tasks]
    profile = db.query(CaseStudentProfile).filter_by(student_case_id=case.id).first()
    student = db.get(User, case.student_id)
    cls = db.get(Class, case.class_id)
    guardians = db.query(StudentGuardian).filter_by(student_id=case.student_id).all()
    guardian_accounts = []
    for link in guardians:
        parent = db.get(User, link.parent_id)
        if parent:
            guardian_accounts.append(
                {"id": link.id, "parent_id": parent.id, "username": parent.username, "name": parent.name, "relationship": link.relationship}
            )
    default_profile = {
        "id": None,
        "student_case_id": case.id,
        "student_name": student.name if student else "",
        "gender": "",
        "ethnicity": "",
        "source_school": "",
        "grade": cls.grade if cls else "",
        "parent_evaluation": "",
        "primary_needs": "",
        "allergy_history": "",
        "underlying_conditions": "",
        "other_health_notes": "",
        "health_visible": True,
        "parent_name": "",
        "parent_phone": "",
        "parent_relationship": "",
        "entrance_scores": "",
        "entrance_total_score": None,
        "entrance_chinese": None,
        "entrance_math": None,
        "entrance_english": None,
        "entrance_physics": None,
        "entrance_chemistry": None,
        "entrance_biology": None,
        "entrance_politics": None,
        "entrance_history": None,
        "entrance_geography": None,
    }
    if profile is not None:
        # SQLAlchemy 对象转 dict 以便做权限过滤，避免直接修改 ORM 导致意外提交
        profile_dict = {c.name: getattr(profile, c.name) for c in CaseStudentProfile.__table__.columns}
        profile_out = _mask_health_for_viewer(profile_dict, user.role)
    else:
        profile_out = default_profile
    review_query = db.query(CaseReview).filter_by(student_case_id=case.id)
    if user.role == ROLE_PARENT:
        # 德育退回意见属于校内协作信息，家长只查看明确共享的督查结论。
        review_query = review_query.filter(CaseReview.visibility == "shared")
        # 家长响应不得包含其他监护人账号/手机号，按矩阵脱敏
        guardian_accounts = []
        # 家长侧不暴露 parent_phone、健康明细等敏感信息
        if isinstance(profile_out, dict):
            profile_out = {
                **profile_out,
                "parent_phone": "",
                "allergy_history": "",
                "underlying_conditions": "",
                "other_health_notes": "",
            }
    return {
        **_case_out(db, case),
        "viewer_role": user.role,
        "can_manage": user.role == ROLE_TEACHER and is_head_teacher(db, case.class_id, user.id),
        "student_profile": profile_out,
        "guardian_accounts": guardian_accounts,
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
        "reviews": review_query.order_by(CaseReview.reviewed_at.desc()).all(),
    }


def _case_out(db: Session, case: StudentCase) -> dict:
    data = StudentCaseOut.model_validate(case).model_dump()
    student = db.get(User, case.student_id)
    profile = db.query(CaseStudentProfile).filter_by(student_case_id=case.id).first()
    cls = db.get(Class, case.class_id)
    data["student_name"] = profile.student_name if profile and profile.student_name else (student.name if student else None)
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
    elif user.role not in (ROLE_ADMIN, ROLE_DEYU_DIRECTOR):
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
    if cycle is None:
        raise HTTPException(status_code=404, detail="学年周期不存在")
    cls = db.get(Class, body.class_id)
    if cls is None:
        raise HTTPException(status_code=404, detail="班级不存在")
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
    elif user.role not in (ROLE_ADMIN, ROLE_DEYU_DIRECTOR):
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
    if case.status not in {"draft", "revision_required"} and changes:
        # 执行中的正式内容不得无痕覆盖；调整前先走复盘状态机。
        raise HTTPException(status_code=409, detail="执行中的总案须先进入阶段复盘并生成新版本")
    for field, value in changes.items():
        setattr(case, field, value)
    audit(db, user.id, "case.update", "student_case", case.id, case.id, {"fields": list(changes)})
    db.commit()
    db.refresh(case)
    return _case_out(db, case)


@router.put("/{case_id}/student-profile", response_model=CaseStudentProfileOut)
def upsert_student_profile(
    case_id: int,
    body: CaseStudentProfileUpsert,
    db: Session = Depends(get_db),
    user: User = Depends(_head_teacher),
):
    case = require_case_access(db, case_id, user, write=True)
    require_case_manager(db, case, user)
    profile = db.query(CaseStudentProfile).filter_by(student_case_id=case.id).first()
    if profile is None:
        profile = CaseStudentProfile(student_case_id=case.id)
        db.add(profile)
    # 基本资料允许在执行期补录，但每次变更都进入总案审计日志。
    changes = body.model_dump()
    for field, value in changes.items():
        setattr(profile, field, value.strip() if isinstance(value, str) else value)
    # 家长手机号格式校验
    parent_phone = (changes.get("parent_phone") or "").strip()
    if parent_phone and not re.fullmatch(r"1[3-9]\d{9}", parent_phone):
        raise HTTPException(status_code=400, detail="家长联系方式需为11位手机号")
    db.flush()
    audit(
        db,
        user.id,
        "student_profile.upsert",
        "case_student_profile",
        profile.id,
        case.id,
        {"fields": list(changes)},
    )
    # 自动注册家长账号：以手机号为用户名，默认密码 88888888
    if parent_phone:
        parent_name = (changes.get("parent_name") or "").strip() or "家长"
        relationship = (changes.get("parent_relationship") or "").strip() or "guardian"
        existing_parent = db.query(User).filter(User.username == parent_phone).first()
        if existing_parent is None:
            parent_user = User(
                username=parent_phone,
                password_hash=hash_password("88888888"),
                name=parent_name,
                role=ROLE_PARENT,
            )
            db.add(parent_user)
            db.flush()
            audit(db, user.id, "parent.auto_create", "user", parent_user.id, case.id, {"username": parent_phone})
        else:
            parent_user = existing_parent
            if parent_user.role != ROLE_PARENT:
                raise HTTPException(status_code=409, detail=f"手机号 {parent_phone} 已被其他角色账号占用")
            # 同步更新家长姓名（若有提供）
            if parent_name != "家长" and parent_user.name != parent_name:
                parent_user.name = parent_name
                db.flush()
        link = db.query(StudentGuardian).filter_by(parent_id=parent_user.id, student_id=case.student_id).first()
        if link is None:
            link = StudentGuardian(parent_id=parent_user.id, student_id=case.student_id, relationship=relationship)
            db.add(link)
            db.flush()
            audit(db, user.id, "guardian.auto_link", "student_guardian", link.id, case.id, {"parent_id": parent_user.id})
        elif relationship and link.relationship != relationship:
            link.relationship = relationship
            db.flush()
    db.commit()
    db.refresh(profile)
    return profile


@router.post("/{case_id}/transition", response_model=StudentCaseOut)
def change_case_status(
    case_id: int,
    body: StudentCaseTransition,
    db: Session = Depends(get_db),
    user: User = Depends(_head_teacher),
):
    case = require_case_access(db, case_id, user, write=True)
    require_case_manager(db, case, user)
    if case.status == CASE_STATUS_PENDING_CONFIRMATION and body.target_status == "executing":
        raise HTTPException(status_code=403, detail="方案须由德育主任审查通过后才能进入执行")
    if case.status == CASE_STATUS_REVISION_REQUIRED and body.target_status == CASE_STATUS_PENDING_CONFIRMATION:
        returned_review = (
            db.query(CaseReview)
            .filter_by(
                student_case_id=case.id,
                review_level="deyu",
                decision="changes_requested",
                workflow_status="open",
                assigned_to=user.id,
            )
            .order_by(CaseReview.reviewed_at.desc())
            .first()
        )
        if returned_review is None:
            raise HTTPException(status_code=409, detail="未找到需要重新提交的德育退回意见")
        returned_review.workflow_status = "resubmitted"
        returned_review.resubmitted_at = datetime.now(timezone.utc)
        audit(
            db,
            user.id,
            "deyu_review.resubmit",
            "case_review",
            returned_review.id,
            case.id,
            {"reason": body.reason, "target_version": returned_review.target_version},
        )
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
    if case.status not in {"draft", "revision_required", "adjusted"}:
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
    if case.status == CASE_STATUS_PENDING_CONFIRMATION:
        raise HTTPException(status_code=409, detail="德育审查期间不能修改任务，请先撤回或等待审查意见")
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
    if case.status == CASE_STATUS_PENDING_CONFIRMATION:
        raise HTTPException(status_code=409, detail="德育审查期间不能修改任务，请先撤回或等待审查意见")
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
    if body.review_level == "deyu":
        raise HTTPException(status_code=400, detail="德育方案审查请使用审查通过或退回修改操作")
    # 权限：校长 -> school/principal；德育主任 -> deyu；班主任 -> head_teacher/subject
    if body.review_level in {"school", "principal"} and user.role != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="校级/校长督查仅校长可提交")
    if body.review_level == "deyu" and user.role != ROLE_DEYU_DIRECTOR:
        raise HTTPException(status_code=403, detail="德育督查仅德育主任可提交")
    if body.review_level not in {"school", "principal", "deyu"}:
        require_case_manager(db, case, user)
    review = CaseReview(student_case_id=case_id, reviewer_id=user.id, **body.model_dump())
    db.add(review)
    db.flush()
    audit(db, user.id, "review.create", "case_review", review.id, case.id, {"level": body.review_level})
    db.commit()
    db.refresh(review)
    return review


@router.post("/{case_id}/deyu-review", response_model=CaseReviewOut)
def decide_deyu_review(
    case_id: int,
    body: DeyuReviewDecision,
    db: Session = Depends(get_db),
    user: User = Depends(_deyu_director),
):
    """德育主任审查班主任方案；通过后发布执行，退回后生成班主任整改待办。"""
    case = require_case_access(db, case_id, user, write=False, subject=body.subject)
    if case.status != CASE_STATUS_PENDING_CONFIRMATION:
        raise HTTPException(status_code=409, detail="仅待德育审查的方案可以执行审查决定")

    now = datetime.now(timezone.utc)
    if body.decision == "changes_requested":
        if not body.problem.strip() or not body.corrective_action.strip() or body.correction_due_on is None:
            raise HTTPException(status_code=400, detail="退回修改必须填写问题、具体修改要求和整改截止日期")
        workflow_status = "open"
        assigned_to = case.owner_teacher_id
        resolved_at = None
        transition_target = CASE_STATUS_REVISION_REQUIRED
        transition_reason = body.corrective_action.strip()
    else:
        # 复审通过时关闭本轮所有已重新提交的退回意见，同时保留每轮审查原文。
        previous_returns = db.query(CaseReview).filter(
            CaseReview.student_case_id == case.id,
            CaseReview.review_level == "deyu",
            CaseReview.decision == "changes_requested",
            CaseReview.workflow_status.in_(["open", "resubmitted"]),
        ).all()
        for returned_review in previous_returns:
            returned_review.workflow_status = "closed"
            returned_review.resolved_at = now
        workflow_status = "closed"
        assigned_to = None
        resolved_at = now
        transition_target = "executing"
        transition_reason = body.corrective_action.strip() or "德育主任审查通过"

    review = CaseReview(
        student_case_id=case.id,
        review_level="deyu",
        subject=body.subject.strip(),
        reviewer_id=user.id,
        problem=body.problem.strip(),
        corrective_action=body.corrective_action.strip(),
        correction_due_on=body.correction_due_on,
        decision=body.decision,
        workflow_status=workflow_status,
        target_version=case.version,
        assigned_to=assigned_to,
        visibility="internal",
        resolved_at=resolved_at,
    )
    db.add(review)
    db.flush()
    audit(
        db,
        user.id,
        "deyu_review.decide",
        "case_review",
        review.id,
        case.id,
        {
            "decision": body.decision,
            "assigned_to": assigned_to,
            "target_version": case.version,
        },
    )
    transition_case(db, case, transition_target, user, transition_reason)
    db.commit()
    db.refresh(review)
    return review
