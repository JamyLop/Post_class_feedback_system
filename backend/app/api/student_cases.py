"""高三一生一案 API：总案、学科方案、目标任务、打卡、督查与版本。"""

from datetime import date, datetime, timezone
from urllib.parse import quote

import re

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_
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
    SubjectSuggestion,
    TaskCheckin,
)
from app.models.user import ROLE_ADMIN, ROLE_CONSULTANT, ROLE_DEYU_DIRECTOR, ROLE_PARENT, ROLE_STUDENT, ROLE_SUBJECT_TEACHER, ROLE_TEACHER, User
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
    SubjectSuggestionCreate,
    SubjectSuggestionOut,
    TaskCheckinCreate,
    TaskCheckinOut,
)
from app.services.student_case_service import (
    PARENT_VISIBLE_STATUSES,
    STUDENT_VISIBLE_STATUSES,
    audit,
    is_head_teacher,
    require_case_access,
    require_case_manager,
    teacher_subjects,
    transition_case,
    verify_case_membership,
)
from app.services.case_export import build_case_export_bytes  # 导出模板变更后触发服务热重载

router = APIRouter(prefix="/student-cases", tags=["student-cases"])
# 校长 + 德育主任 + 班主任 + 咨询老师 + 任课老师均可查看督查进度；仅班主任可写
_staff = require_roles([ROLE_ADMIN, ROLE_DEYU_DIRECTOR, ROLE_TEACHER, ROLE_CONSULTANT, ROLE_SUBJECT_TEACHER])
_head_teacher = require_roles([ROLE_TEACHER])
# 学科建议提出人：非班主任的教师（含任课老师）；班主任请直接维护学科方案
_suggestion_author = require_roles([ROLE_TEACHER, ROLE_SUBJECT_TEACHER])
_deyu_director = require_roles([ROLE_DEYU_DIRECTOR])


def _mask_health_for_viewer(profile_data: dict, viewer_role: str) -> dict:
    """按健康单项脱敏；旧 health_visible=False 时继续整体隐藏，兼容历史档案。"""
    if viewer_role == ROLE_ADMIN:
        return profile_data
    masked = dict(profile_data)
    legacy_hidden = profile_data.get("health_visible") is False
    fields = {
        "allergy_history": "allergy_visible",
        "underlying_conditions": "underlying_conditions_visible",
        "other_health_notes": "other_health_notes_visible",
    }
    for value_field, visible_field in fields.items():
        if legacy_hidden or profile_data.get(visible_field) is False:
            masked[value_field] = ""
    return masked


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
        "allergy_visible": True,
        "underlying_conditions_visible": True,
        "other_health_notes_visible": True,
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
        # 关键修复：建档时家长联系方式仅写入 StudentGuardian，新建总案未回填到
        # case_student_profiles，导致详情页“三栏”显示暂未填写。存量数据在此做
        # 展示层兜底 + 惰性回写，下次查询即持久一致。
        student_backfill_fields: list[str] = []
        if student is not None:
            for fld in ("gender", "ethnicity", "source_school", "grade"):
                if not (profile_dict.get(fld) or "").strip():
                    val = getattr(student, fld, "") or ""
                    if val:
                        profile_dict[fld] = val
                        if fld != "grade":  # grade 仅展示兜底，避免覆盖档案年级
                            student_backfill_fields.append(fld)
            if not (profile_dict.get("student_name") or "").strip() and student.name:
                profile_dict["student_name"] = student.name
                student_backfill_fields.append("student_name")
        needs_backfill = False
        if not (profile_dict.get("parent_name") or "").strip() or not (profile_dict.get("parent_phone") or "").strip():
            if guardian_accounts:
                first = guardian_accounts[0]
                if not (profile_dict.get("parent_name") or "").strip():
                    profile_dict["parent_name"] = first["name"] or ""
                    needs_backfill = True
                if not (profile_dict.get("parent_phone") or "").strip():
                    profile_dict["parent_phone"] = first["username"] or ""
                    needs_backfill = True
                if not (profile_dict.get("parent_relationship") or "").strip():
                    profile_dict["parent_relationship"] = first["relationship"] or ""
                    needs_backfill = True
        if needs_backfill or student_backfill_fields:
            try:
                for fld in ("parent_name", "parent_phone", "parent_relationship"):
                    if profile_dict.get(fld) and not (getattr(profile, fld, "") or "").strip():
                        setattr(profile, fld, profile_dict[fld])
                for fld in student_backfill_fields:
                    if profile_dict.get(fld) and not (getattr(profile, fld, "") or "").strip():
                        setattr(profile, fld, profile_dict[fld])
                db.flush()
                db.commit()
            except Exception:
                db.rollback()
        profile_out = _mask_health_for_viewer(profile_dict, user.role)
    else:
        # 尚未建档案明细时也用监护人/学生表兜底，避免新建学生后档案页直接显示空白
        if student is not None:
            for fld in ("gender", "ethnicity", "source_school"):
                if getattr(student, fld, ""):
                    default_profile[fld] = getattr(student, fld)
            if student.name:
                default_profile["student_name"] = student.name
        if guardian_accounts:
            first = guardian_accounts[0]
            default_profile["parent_name"] = first["name"] or ""
            default_profile["parent_phone"] = first["username"] or ""
            default_profile["parent_relationship"] = first["relationship"] or ""
        profile_out = default_profile
    review_query = db.query(CaseReview).filter_by(student_case_id=case.id)
    if user.role == ROLE_PARENT:
        # 家长端不展示督查复盘
        review_query = None
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
    if user.role == ROLE_STUDENT:
        # 学生自查：不暴露其他监护人账号，不暴露健康明细（按矩阵）
        review_query = review_query.filter(CaseReview.visibility == "shared")
        guardian_accounts = []
        if isinstance(profile_out, dict):
            profile_out = {
                **profile_out,
                "parent_phone": "",
                "allergy_history": "",
                "underlying_conditions": "",
                "other_health_notes": "",
            }
    if user.role == ROLE_CONSULTANT:
        # 咨询老师：不暴露督查复盘，不暴露健康明细
        review_query = review_query.filter(False)
        guardian_accounts = []
        if isinstance(profile_out, dict):
            profile_out = {
                **profile_out,
                "parent_phone": "",
                "allergy_history": "",
                "underlying_conditions": "",
                "other_health_notes": "",
            }
    # 任课老师：与班主任同等的档案可见性（健康按档案可见性开关脱敏），
    # 仅学科方案列表按所带学科过滤（见下方 subject_plans），修改走学科建议链路。
    result = {
        **_case_out(db, case),
        "viewer_role": user.role,
        "can_manage": user.role == ROLE_TEACHER and is_head_teacher(db, case.class_id, user.id),
        "student_profile": profile_out,
        "guardian_accounts": guardian_accounts,
        "subject_plans": (
            db.query(SubjectPlan).filter_by(student_case_id=case.id).filter(
                or_(SubjectPlan.teacher_id == user.id, SubjectPlan.subject.in_(teacher_subjects(db, case.class_id, user.id)))
            ).order_by(SubjectPlan.id).all()
            if (user.role == ROLE_TEACHER and not is_head_teacher(db, case.class_id, user.id))
            or user.role == ROLE_SUBJECT_TEACHER
            else db.query(SubjectPlan).filter_by(student_case_id=case.id).order_by(SubjectPlan.id).all()
        ),
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
    }
    if review_query is not None:
        result["reviews"] = review_query.order_by(CaseReview.reviewed_at.desc()).all()
    return result


def _case_out(db: Session, case: StudentCase) -> dict:
    data = StudentCaseOut.model_validate(case).model_dump()
    student = db.get(User, case.student_id)
    profile = db.query(CaseStudentProfile).filter_by(student_case_id=case.id).first()
    cls = db.get(Class, case.class_id)
    data["student_name"] = profile.student_name if profile and profile.student_name else (student.name if student else None)
    data["class_name"] = cls.name if cls else None
    data["class_starts_on"] = cls.school_year_starts_on if cls else None
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


@router.get("/my-case", response_model=StudentCaseDetail)
def my_case(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles([ROLE_STUDENT])),
):
    """学生自查：返回本人最新一条可见状态的总案详情。"""
    case = (
        db.query(StudentCase)
        .filter(
            StudentCase.student_id == user.id,
            StudentCase.status.in_(STUDENT_VISIBLE_STATUSES),
        )
        .order_by(StudentCase.updated_at.desc())
        .first()
    )
    if case is None:
        raise HTTPException(status_code=404, detail="暂无可查看档案")
    return _detail(db, case, user)


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
        if user.role == ROLE_SUBJECT_TEACHER and not teacher_subjects(db, class_id, user.id):
            raise HTTPException(status_code=403, detail="无权查看该班级进展")
        query = query.filter(StudentCase.class_id == class_id)
    elif user.role == ROLE_CONSULTANT:
        # 咨询老师只能查看关联学生的档案
        from app.models.class_ import StudentConsultant
        student_ids = [
            row.student_id
            for row in db.query(StudentConsultant).filter_by(consultant_id=user.id).all()
        ]
        query = query.filter(StudentCase.student_id.in_(student_ids))
    elif user.role == ROLE_SUBJECT_TEACHER:
        # 任课老师只能查看所带学科班级的档案
        class_ids = [
            row.class_id
            for row in db.query(ClassTeacher).filter(ClassTeacher.teacher_id == user.id).all()
        ]
        query = query.filter(StudentCase.class_id.in_(class_ids or [-1]))
    elif user.role == ROLE_TEACHER:
        legacy_ids = [row.id for row in db.query(Class).filter(Class.teacher_id == user.id)]
        relation_ids = [row.class_id for row in db.query(ClassTeacher).filter(ClassTeacher.teacher_id == user.id)]
        plan_case_ids = [row.student_case_id for row in db.query(SubjectPlan).filter(SubjectPlan.teacher_id == user.id)]
        query = query.filter(or_(StudentCase.class_id.in_(set(legacy_ids + relation_ids)), StudentCase.id.in_(plan_case_ids or [-1])))
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
    # 家庭反馈属于学生基本资料，不得混入总体问题和升学目标等总案诊断字段。
    case_data = body.model_dump(exclude={"parent_evaluation", "primary_needs"})
    case = StudentCase(**case_data)
    db.add(case)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="该学生在此周期已有总案") from exc
    student = db.get(User, body.student_id)
    # 新建总案时同步入学时已录的家长联系方式，避免档案页显示空白
    guardian_link = db.query(StudentGuardian).filter_by(student_id=body.student_id).first()
    guardian_parent = db.get(User, guardian_link.parent_id) if guardian_link else None
    profile = CaseStudentProfile(
        student_case_id=case.id,
        student_name=student.name if student else "",
        gender=getattr(student, "gender", "") or "",
        ethnicity=getattr(student, "ethnicity", "") or "",
        source_school=getattr(student, "source_school", "") or "",
        grade=getattr(student, "grade", "") or cls.grade or "",
        parent_evaluation=body.parent_evaluation.strip(),
        primary_needs=body.primary_needs.strip(),
        parent_name=guardian_parent.name if guardian_parent else "",
        parent_phone=guardian_parent.username if guardian_parent else "",
        parent_relationship=guardian_link.relationship if guardian_link else "",
    )
    db.add(profile)
    db.flush()
    audit(db, user.id, "case.create", "student_case", case.id, case.id)
    audit(
        db,
        user.id,
        "student_profile.create",
        "case_student_profile",
        profile.id,
        case.id,
        {"fields": ["student_name", "grade", "parent_evaluation", "primary_needs"]},
    )
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
    elif user.role == ROLE_STUDENT:
        query = query.filter(
            StudentCase.student_id == user.id,
            StudentCase.status.in_(STUDENT_VISIBLE_STATUSES),
        )
    elif user.role == ROLE_CONSULTANT:
        # 咨询老师只能查看关联学生的档案
        from app.models.class_ import StudentConsultant
        student_ids = [
            row.student_id
            for row in db.query(StudentConsultant).filter_by(consultant_id=user.id).all()
        ]
        query = query.filter(StudentCase.student_id.in_(student_ids))
    elif user.role == ROLE_SUBJECT_TEACHER:
        # 任课老师只能查看所带学科班级的档案
        class_ids = [
            row.class_id
            for row in db.query(ClassTeacher).filter(ClassTeacher.teacher_id == user.id).all()
        ]
        query = query.filter(StudentCase.class_id.in_(class_ids or [-1]))
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
    # 正式版式需要档案与教师姓名（档案取 _detail 已脱敏/兜底后的展示版，保证无档案时也能导出）
    teacher_ids = {p.teacher_id for p in detail["subject_plans"] if getattr(p, "teacher_id", None)}
    teacher_names: dict[int, str] = {}
    if teacher_ids:
        for u in db.query(User).filter(User.id.in_(teacher_ids)).all():
            teacher_names[u.id] = u.name
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
        profile=detail.get("student_profile"),
        goals=detail["goals"],
        guardians=detail["guardian_accounts"],
        teacher_names=teacher_names,
    )
    audit(db, user.id, "case.export", "student_case", case.id, case.id, {"version": case.version, "status": case.status})
    db.commit()
    filename = f"{student.name if student else case.student_id}_一生一案_V{case.version}_全铺满封面_{datetime.now(timezone.utc).strftime('%Y%m%d')}.docx"
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}; filename=\"export.docx\"",
            "X-Case-Version": str(case.version),
            "X-Case-Status": case.status,
            "X-Case-Export-Implementation": "docx-cover-full-bleed-v2",
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
    # 自动同步 class_teachers：确保该任课老师与班级关联
    if body.teacher_id:
        exists = db.query(ClassTeacher).filter_by(
            class_id=case.class_id, teacher_id=body.teacher_id, subject=subject
        ).first()
        if not exists:
            db.add(ClassTeacher(
                class_id=case.class_id,
                teacher_id=body.teacher_id,
                role="subject_teacher",
                subject=subject,
            ))
    db.flush()
    audit(db, user.id, "subject_plan.upsert", "subject_plan", plan.id, case.id, {"subject": subject})
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/{case_id}/subject-suggestions", response_model=list[SubjectSuggestionOut])
def list_subject_suggestions(case_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_case_access(db, case_id, user)
    query = db.query(SubjectSuggestion).filter_by(student_case_id=case_id)
    if user.role == ROLE_TEACHER and not is_head_teacher(db, db.get(StudentCase, case_id).class_id, user.id):
        query = query.filter(SubjectSuggestion.teacher_id == user.id)
    if user.role == ROLE_SUBJECT_TEACHER:
        query = query.filter(SubjectSuggestion.teacher_id == user.id)
    return query.order_by(SubjectSuggestion.created_at.desc()).all()


@router.post("/{case_id}/subject-suggestions", response_model=SubjectSuggestionOut)
def create_subject_suggestion(case_id: int, body: SubjectSuggestionCreate, db: Session = Depends(get_db), user: User = Depends(_suggestion_author)):
    case = require_case_access(db, case_id, user)
    if user.role == ROLE_TEACHER and is_head_teacher(db, case.class_id, user.id):
        raise HTTPException(status_code=403, detail="班主任请直接维护学科方案")
    if body.subject not in teacher_subjects(db, case.class_id, user.id):
        raise HTTPException(status_code=403, detail="无权对该学科提出建议")
    suggestion = SubjectSuggestion(student_case_id=case_id, teacher_id=user.id, **body.model_dump())
    db.add(suggestion)
    db.commit()
    db.refresh(suggestion)
    return suggestion


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
    # 阶段归属：任务创建时快照总案当前版本，阶段即版本
    task = CaseTask(student_case_id=case_id, created_by=user.id, version=case.version, **body.model_dump())
    db.add(task)
    db.flush()
    audit(db, user.id, "task.create", "case_task", task.id, case.id)
    from app.services.case_points_service import recompute_stage_completion as _recompute

    _recompute(db, case, recorded_by=user.id)
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
        # points 有缺省值：未显式传入时保持原权重，避免编辑标题时重置积分
        if field == "points" and "points" not in body.model_fields_set:
            continue
        setattr(task, field, value)
    audit(db, user.id, "task.update", "case_task", task.id, case.id)
    from app.services.case_points_service import recompute_stage_completion as _recompute_task

    _recompute_task(db, case, recorded_by=user.id)
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
    # 执行记录由班主任代为确认录入，student_id 始终指向记录所属学生；
    # earned_points 按任务满分积分 × 完成率折算，log_date 为每日记录日期。
    from datetime import date as _date

    from app.services.case_points_service import earned_of as _earned_of
    from app.services.case_points_service import recompute_stage_completion as _recompute_checkin

    checkin = TaskCheckin(
        task_id=task.id,
        student_id=case.student_id,
        completion_rate=body.completion_rate,
        self_check=body.self_check,
        earned_points=_earned_of(task.points or 0, body.completion_rate),
        log_date=body.log_date or _date.today(),
    )
    db.add(checkin)
    if body.completion_rate == 100:
        task.status = "completed"
    elif body.completion_rate > 0:
        task.status = "in_progress"
    db.flush()
    audit(db, user.id, "task.checkin", "task_checkin", checkin.id, case.id, {"rate": body.completion_rate})
    _recompute_checkin(db, case, recorded_by=user.id)
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
