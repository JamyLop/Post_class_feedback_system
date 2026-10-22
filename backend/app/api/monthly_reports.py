"""月度评定 API：班主任手动填写、保存与发布；任课老师独立提交学科评价。"""

import calendar
import logging
from collections import defaultdict
from datetime import date
from typing import Literal
from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.auth.deps import get_current_user, require_roles
from app.core.database import get_db
from app.services.supervision_scope import can_supervise_class, supervised_class_ids
from app.services.class_transfer_service import (
    historical_roster, frozen_report_context, can_read_transferred_history, current_head_student_ids,
    same_roster_scope,
)
from app.models.class_transfer import ClassTransferItem
from app.models.class_ import Class, ClassStudent, ClassTeacher, StudentGuardian
from app.models.monthly_report import (
    MONTHLY_EVAL_ROLE_HEAD,
    MONTHLY_EVAL_ROLE_SUBJECT,
    MONTHLY_STATUS_FAILED,
    MONTHLY_STATUS_GENERATED,
    MONTHLY_STATUS_GENERATING,
    MONTHLY_STATUS_PUBLISHED,
    MonthlyReport,
    MonthlyReportEvaluation,
)
from app.models.student_case import StudentCase, SubjectPlan
from app.models.user import (
    ROLE_ADMIN,
    ROLE_PARENT,
    ROLE_STUDENT,
    ROLE_SUBJECT_TEACHER,
    ROLE_TEACHER,
    User,
)
from app.schemas.monthly_report import (
    MonthlyEvaluationSave,
    MonthlyReportCreateIn,
    MonthlyReportOut,
    MonthlyReportUpdateIn,
    MonthlyReportMonthIn,
    MonthlyWritingStatusOut,
)

router = APIRouter(prefix="/monthly-reports", tags=["monthly-reports"])
_manager = require_roles([ROLE_ADMIN, ROLE_TEACHER, ROLE_SUBJECT_TEACHER])
_evaluator = require_roles([ROLE_TEACHER, ROLE_SUBJECT_TEACHER])
logger = logging.getLogger(__name__)

def _month_bounds(label: str) -> tuple[date, date]:
    try:
        y, m = map(int, label.split("-"))
        last = calendar.monthrange(y, m)[1]
        return date(y, m, 1), date(y, m, last)
    except Exception:
        raise HTTPException(status_code=400, detail="month_label 需为 YYYY-MM 格式")

def _enrich(row: MonthlyReport, db: Session, user: User) -> dict:
    data = MonthlyReportOut.model_validate(row).model_dump()
    stu = db.get(User, row.student_id)
    cls = db.get(Class, row.class_id)
    data["student_name"] = stu.name if stu else None
    data["class_name"] = cls.name if cls else None
    role_subject = _evaluation_role(db, row, user)
    data["can_evaluate"] = role_subject is not None
    data["evaluation_subject"] = role_subject[1] if role_subject else ""
    frozen = frozen_report_context(db, row) is not None
    data["can_manage"] = not frozen and _is_head_teacher(db, row.class_id, user)
    data["can_publish"] = not frozen and (data["can_manage"] or user.role == ROLE_ADMIN)
    return data


def _evaluation_role(db: Session, row: MonthlyReport, user: User) -> tuple[str, str] | None:
    """判定用户可否评价该月度评定；返回 (role, subject)，班主任 subject 为空。"""
    if user.role not in (ROLE_TEACHER, ROLE_SUBJECT_TEACHER):
        return None
    if frozen_report_context(db, row) is not None:
        return None
    cls = db.get(Class, row.class_id)
    relations = db.query(ClassTeacher).filter_by(class_id=row.class_id, teacher_id=user.id).all()
    # 学生档案中的任课安排优先于班级关系，避免同班其他老师代填。
    case = db.get(StudentCase, row.student_case_id) if row.student_case_id else db.query(StudentCase).filter_by(
        student_id=row.student_id, class_id=row.class_id,
    ).filter(StudentCase.status != "archived").order_by(StudentCase.id.desc()).first()
    plans = db.query(SubjectPlan).filter_by(student_case_id=case.id).all() if case else []
    head_subjects = {r.subject for r in db.query(ClassTeacher).filter_by(
        class_id=row.class_id, teacher_id=cls.teacher_id, role="subject_teacher",
    ).all()} if case and cls and case.owner_teacher_id == cls.teacher_id else set()
    return _resolve_evaluation_role(cls, relations, case, plans, head_subjects, user)


def _resolve_evaluation_role(cls, relations, case, plans, head_subjects, user):
    """查询和保存共用同一任课判定，批量查询时复用已加载的关系。"""
    is_head = (cls is not None and cls.teacher_id == user.id) or any(r.role == "head_teacher" for r in relations)
    initial_subjects = {p.subject.strip() for p in plans}
    if case and cls and case.owner_teacher_id == cls.teacher_id:
        # 旧档案以班主任占位任课 ID；没有明确兼教学科时，不能覆盖班级任课安排。
        # 其他老师的学生专属安排仍优先，班主任明确兼教的学科也保留。
        plans = [p for p in plans if p.teacher_id != cls.teacher_id or p.subject in head_subjects]
    assigned = {p.subject for p in plans if p.teacher_id == user.id}
    configured = {p.subject for p in plans}
    assigned.update(r.subject for r in relations if r.role == "subject_teacher" and r.subject and r.subject not in configured)
    # 德育统一由班主任正文承载，历史任课关系中的德育不能再生成学科评定。
    assigned = {subject for subject in assigned if subject.strip() != "德育"}
    # 班级关系只解析初评科目的负责人，不能给该生增加未建立初评的科目。
    assigned &= initial_subjects
    if assigned:
        return (MONTHLY_EVAL_ROLE_SUBJECT, "、".join(sorted(assigned)))
    if is_head:
        return (MONTHLY_EVAL_ROLE_HEAD, "")
    return None


def _is_head_teacher(db: Session, class_id: int, user: User) -> bool:
    if user.role not in (ROLE_TEACHER, ROLE_SUBJECT_TEACHER):
        return False
    cls = db.get(Class, class_id)
    return bool((cls and cls.teacher_id == user.id) or db.query(ClassTeacher).filter_by(
        class_id=class_id, teacher_id=user.id, role="head_teacher",
    ).first())


def _require_manager(db: Session, class_id: int, user: User):
    # 管理员保留发布管理权限；德育正文只能由本班班主任填写。
    if not _is_head_teacher(db, class_id, user):
        raise HTTPException(status_code=403, detail="德育月度评定仅由本班班主任填写")


def _subject_teacher_class_ids(db: Session, user: User) -> set[int]:
    rows = db.query(ClassTeacher).filter_by(teacher_id=user.id).all()
    plan_classes = db.query(StudentCase.class_id).join(SubjectPlan, SubjectPlan.student_case_id == StudentCase.id).filter(
        SubjectPlan.teacher_id == user.id, StudentCase.class_id.isnot(None), StudentCase.status != "archived",
    ).all()
    return {r.class_id for r in rows} | {r.class_id for r in plan_classes}

def _authorize_student_class(db: Session, student_id: int, class_id: int, user: User):
    cls = db.get(Class, class_id)
    if cls is None:
        raise HTTPException(status_code=404, detail="班级不存在")
    if user.role == ROLE_TEACHER and cls.teacher_id != user.id:
        # 也允许通过 ClassTeacher 关联
        if not db.query(ClassTeacher).filter_by(class_id=class_id, teacher_id=user.id).first():
            raise HTTPException(status_code=403, detail="无权操作该班级月度评定")
    if user.role == ROLE_SUBJECT_TEACHER:
        if not db.query(ClassTeacher).filter_by(class_id=class_id, teacher_id=user.id).first():
            raise HTTPException(status_code=403, detail="无权查看该班级月度评定")
    member = db.query(ClassStudent).filter(ClassStudent.class_id == class_id, ClassStudent.student_id == student_id).first()
    if member is None:
        raise HTTPException(status_code=403, detail="学生不属于该班级")

def _report_access(db: Session, report_id: int, user: User) -> MonthlyReport:
    r = db.get(MonthlyReport, report_id)
    if r is None:
        raise HTTPException(status_code=404, detail="月度评定不存在")
    if user.role == ROLE_ADMIN:
        return r
    if can_supervise_class(db, user, r.class_id):
        return r
    if user.role == ROLE_STUDENT:
        if r.student_id != user.id or r.status != MONTHLY_STATUS_PUBLISHED:
            raise HTTPException(status_code=403, detail="无权查看该月度评定")
        return r
    if user.role == ROLE_PARENT:
        linked = db.query(StudentGuardian).filter_by(parent_id=user.id, student_id=r.student_id).first()
        if linked is None or r.status != MONTHLY_STATUS_PUBLISHED:
            raise HTTPException(status_code=403, detail="无权查看该月度评定")
        return r
    if can_read_transferred_history(db, user, r.student_id, r.class_id):
        return r
    if frozen_report_context(db, r) is not None and _is_head_teacher(db, r.class_id, user):
        return r
    if _evaluation_role(db, r, user) is not None:
        return r
    if user.role == ROLE_SUBJECT_TEACHER:
        # 任课老师可查看所带班级的全部状态评定，以便在发布前提交学科评价。
        if not db.query(ClassTeacher).filter_by(class_id=r.class_id, teacher_id=user.id).first():
            raise HTTPException(status_code=403, detail="无权查看该月度评定")
        return r
    _authorize_student_class(db, r.student_id, r.class_id, user)
    return r


def _require_unfrozen(db, report):
    if frozen_report_context(db, report) is not None:
        raise HTTPException(409, "该月评已作为调班前的历史记录保留，仅可查看")

@router.post("/generate")
def generate_monthly(user: User = Depends(_manager)):
    # 老客户端必须升级，不能继续触发 AI 或覆盖教师已保存的正文。
    raise HTTPException(status_code=410, detail="月度评定已改为手动填写，请更新客户端后新建评定")


@router.post("", response_model=MonthlyReportOut)
def create_monthly(
    body: MonthlyReportCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(_manager),
):
    stu = db.query(User).filter_by(id=body.student_id).with_for_update().first()
    if stu is None or stu.role != ROLE_STUDENT:
        raise HTTPException(status_code=404, detail="学生不存在")
    if not db.query(ClassStudent).filter_by(student_id=body.student_id, class_id=body.class_id).first():
        raise HTTPException(status_code=403, detail="学生不属于该班级")
    scope = MonthlyReport(student_id=body.student_id, class_id=body.class_id, student_case_id=body.student_case_id)
    role_subject = (MONTHLY_EVAL_ROLE_HEAD, "") if _is_head_teacher(db, body.class_id, user) else _evaluation_role(db, scope, user)
    if body.evaluation_role == MONTHLY_EVAL_ROLE_SUBJECT:
        role_subject = _evaluation_role(db, scope, user)
        if role_subject and role_subject[0] != MONTHLY_EVAL_ROLE_SUBJECT:
            role_subject = None
    elif body.evaluation_role == MONTHLY_EVAL_ROLE_HEAD and not _is_head_teacher(db, body.class_id, user):
        role_subject = None
    if role_subject is None:
        raise HTTPException(status_code=403, detail="仅对应任课老师或本班班主任可填写")
    period_start, period_end = _month_bounds(body.month_label)
    period_members, _ = historical_roster(db, body.month_label, {body.class_id}, body.student_id)
    if not period_members:
        raise HTTPException(409, "该学生在所选月份不属于此班级，请查看原班历史评定")
    for previous in db.query(MonthlyReport).filter_by(student_id=body.student_id, month_label=body.month_label,
                                                     status=MONTHLY_STATUS_PUBLISHED):
        if previous.class_id != body.class_id and frozen_report_context(db, previous) is not None and same_roster_scope(
            db.get(Class, previous.class_id), db.get(Class, body.class_id)):
            raise HTTPException(409, "该学生本月已有调班前发布的月评，请查看历史记录，无需重复填写")
    if body.student_case_id is not None:
        sc = db.get(StudentCase, body.student_case_id)
        if sc is None or sc.student_id != body.student_id or sc.class_id != body.class_id:
            raise HTTPException(status_code=400, detail="student_case_id 与学生/班级不匹配")
    # 锁定学生，串行检查同班同月重复创建，防止双击或并发请求覆盖手写内容。
    db.query(User).filter(User.id == body.student_id).with_for_update().first()
    existing = db.query(MonthlyReport).filter_by(
        student_id=body.student_id, class_id=body.class_id, month_label=body.month_label,
    ).first()
    if existing:
        # 任课老师先填写后，班主任可补上德育，不覆盖已提交的学科内容。
        if role_subject[0] == MONTHLY_EVAL_ROLE_HEAD and not existing.final_content.strip():
            existing.final_content = body.final_content
            existing.reviewed_by = user.id
            db.commit()
            db.refresh(existing)
            return _enrich(existing, db, user)
        raise HTTPException(status_code=409, detail="该学生本月已有评定，请打开原评定填写")
    report = MonthlyReport(
        student_id=body.student_id, class_id=body.class_id,
        student_case_id=body.student_case_id, month_label=body.month_label,
        period_start=period_start, period_end=period_end,
        # 沿用 generated 存储值表示待发布，兼容历史记录且无需迁移。
        status=MONTHLY_STATUS_GENERATED, final_content=body.final_content if role_subject[0] == MONTHLY_EVAL_ROLE_HEAD else "",
        reviewed_by=user.id, prompt_version="manual_v1", input_snapshot={},
    )
    db.add(report)
    if role_subject[0] == MONTHLY_EVAL_ROLE_SUBJECT:
        # 学科老师可直接开始本月评定，无需等待班主任先建记录。
        if len(body.final_content) > 2000:
            raise HTTPException(status_code=422, detail="学科评定最多2000字")
        report.evaluations.append(MonthlyReportEvaluation(
            teacher_id=user.id, teacher_name=user.name, teacher_role=role_subject[0],
            subject=role_subject[1], content=body.final_content,
        ))
    db.commit()
    db.refresh(report)
    return _enrich(report, db, user)

@router.get("", response_model=list[MonthlyReportOut])
def list_reports(
    student_id: int | None = Query(default=None),
    class_id: int | None = Query(default=None),
    month_label: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(MonthlyReport)
    if user.role == ROLE_STUDENT:
        q = q.filter(MonthlyReport.student_id == user.id, MonthlyReport.status == MONTHLY_STATUS_PUBLISHED)
    elif user.role == ROLE_PARENT:
        student_ids = [r.student_id for r in db.query(StudentGuardian).filter_by(parent_id=user.id).all()]
        if not student_ids:
            return []
        q = q.filter(MonthlyReport.student_id.in_(student_ids), MonthlyReport.status == MONTHLY_STATUS_PUBLISHED)
    elif user.role == ROLE_TEACHER:
        # 教师仅看自己班级
        legacy_ids = [r.id for r in db.query(Class).filter(Class.teacher_id == user.id).all()]
        rel_ids = [r.class_id for r in db.query(ClassTeacher).filter(ClassTeacher.teacher_id == user.id).all()]
        allowed = set(legacy_ids + rel_ids) | _subject_teacher_class_ids(db, user)
        if not allowed:
            return []
        history_scope = and_(MonthlyReport.student_id.in_(current_head_student_ids(db, user)),
            db.query(ClassTransferItem.id).filter(ClassTransferItem.student_id == MonthlyReport.student_id,
                ClassTransferItem.source_class_id == MonthlyReport.class_id).exists())
        q = q.filter(or_(MonthlyReport.class_id.in_(allowed), history_scope))
    elif user.role == ROLE_SUBJECT_TEACHER:
        # 教学管理仅列本人任教班级；主管的学段进度在主管工作台查询。
        allowed = _subject_teacher_class_ids(db, user)
        if not allowed:
            return []
        q = q.filter(MonthlyReport.class_id.in_(allowed))
    elif user.role not in (ROLE_ADMIN,):
        # 德育主任、咨询老师等暂不开放月度评定列表。
        return []
    # 管理员不过滤
    if student_id is not None:
        q = q.filter(MonthlyReport.student_id == student_id)
    if class_id is not None:
        if user.role == ROLE_TEACHER and _is_head_teacher(db, class_id, user):
            member_ids = db.query(ClassStudent.student_id).filter_by(class_id=class_id).scalar_subquery()
            q = q.filter(or_(MonthlyReport.class_id == class_id, and_(MonthlyReport.student_id.in_(member_ids), history_scope)))
        else:
            q = q.filter(MonthlyReport.class_id == class_id)
    if month_label:
        q = q.filter(MonthlyReport.month_label == month_label)
    if status:
        q = q.filter(MonthlyReport.status == status)
    rows = q.order_by(MonthlyReport.month_label.desc(), MonthlyReport.created_at.desc()).offset(offset).limit(limit).all()
    return [_enrich(r, db, user) for r in rows]

@router.get("/writing-status", response_model=MonthlyWritingStatusOut)
def writing_status(
    month_label: str = Query(pattern=r"^\d{4}-\d{2}$"),
    class_id: int | None = Query(default=None),
    student_id: int | None = Query(default=None),
    writing_status: Literal["written", "unwritten"] | None = Query(default=None),
    view: Literal["items", "students"] = Query(default="items"),
    scope: Literal["teaching", "supervision"] = Query(default="teaching"),
    keyword: str = Query(default="", max_length=100),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(_manager),
):
    _month_bounds(month_label)
    is_admin = user.role == ROLE_ADMIN
    is_supervision = scope == "supervision"
    allowed = {c.id for c in db.query(Class).all()} if is_admin else _subject_teacher_class_ids(db, user) | {
        c.id for c in db.query(Class).filter_by(teacher_id=user.id).all()
    }
    if is_supervision:
        allowed = supervised_class_ids(db, user)
    if class_id is not None:
        allowed &= {class_id}
    classes = {c.id: c for c in db.query(Class).filter(Class.id.in_(allowed)).all()}
    relations = defaultdict(list)
    for relation in db.query(ClassTeacher).filter(ClassTeacher.class_id.in_(allowed)).all():
        relations[relation.class_id].append(relation)
    members, historic_contexts = historical_roster(db, month_label, allowed, student_id)
    student_ids = {student.id for _, student in members}
    cases = db.query(StudentCase).filter(StudentCase.student_id.in_(student_ids)).order_by(StudentCase.id.desc()).all()
    cases_by_id = {case.id: case for case in cases}
    latest_cases = {}
    for case in cases:
        if case.status != "archived":
            latest_cases.setdefault((case.class_id, case.student_id), case)
    plans = defaultdict(list)
    for plan in db.query(SubjectPlan).filter(SubjectPlan.student_case_id.in_(cases_by_id)).all():
        plans[plan.student_case_id].append(plan)
    teacher_ids = {r.teacher_id for group in relations.values() for r in group}
    teacher_ids.update(p.teacher_id for group in plans.values() for p in group)
    teacher_ids.update(c.teacher_id for c in classes.values())
    for context in historic_contexts.values():
        teacher_ids.add(context["source"]["teacher_id"])
        teacher_ids.update(p["teacher_id"] for snap in context["cases"] for p in snap["subject_plans"])
        teacher_ids.update(r["teacher_id"] for r in context["relations"])
    teacher_ids.add(user.id)
    teachers = {t.id: t for t in db.query(User).filter(
        User.id.in_(teacher_ids), User.role.in_([ROLE_TEACHER, ROLE_SUBJECT_TEACHER]),
    ).all()}
    reports = {(r.class_id, r.student_id): r for r in db.query(MonthlyReport).filter(
        MonthlyReport.class_id.in_(allowed), MonthlyReport.student_id.in_(student_ids),
        MonthlyReport.month_label == month_label,
    ).all()}
    # 当月已发布的旧班月评继续作为该生本月成果，避免新班再次产生催填。
    published_history = {}
    for report in db.query(MonthlyReport).filter(MonthlyReport.student_id.in_(student_ids),
        MonthlyReport.month_label == month_label, MonthlyReport.status == MONTHLY_STATUS_PUBLISHED):
        context = frozen_report_context(db, report)
        if context:
            published_history[report.student_id] = (report, context)
    rows = []
    student_scopes = {}
    for member, student in members:
        cls = classes[member.class_id]
        if keyword.strip().casefold() not in f"{student.name} {cls.name}".casefold():
            continue
        own_relations = [r for r in relations[cls.id] if r.teacher_id == user.id]
        # 主管的管理职责仅在 supervision 查询生效，日常任课查询仍按本人职责汇总。
        is_head = is_admin or is_supervision or cls.teacher_id == user.id or any(r.role == "head_teacher" for r in own_relations)
        report = reports.get((cls.id, student.id))
        case = cases_by_id.get(report.student_case_id) if report and report.student_case_id else latest_cases.get((cls.id, student.id))
        case_plans = plans[case.id] if case else []
        duty_cls, duty_relations = cls, relations[cls.id]
        context = historic_contexts.get((cls.id, student.id))
        if not report and student.id in published_history:
            previous_report, previous_context = published_history[student.id]
            if same_roster_scope(cls, SimpleNamespace(**previous_context["source"])):
                report, context = previous_report, previous_context
        if context:
            duty_cls = SimpleNamespace(**context["source"])
            duty_relations = [SimpleNamespace(**r) for r in context["relations"] if r["class_id"] == duty_cls.id]
            snapshots = context["cases"]
            snapshot = next((s for s in snapshots if report and s["case"]["id"] == report.student_case_id),
                            snapshots[-1] if snapshots and not (report and report.student_case_id) else None)
            if snapshot:
                case = SimpleNamespace(**snapshot["case"])
                case_plans = [SimpleNamespace(**p) for p in snapshot["subject_plans"]]
            # 过去的老师仍按原职责计数；不会因交接后的 teacher_id 变化把已填误报未填。
            for tid in {duty_cls.teacher_id} | {p.teacher_id for p in case_plans} | {r.teacher_id for r in duty_relations}:
                if tid not in teachers and (teacher := db.get(User, tid)) is not None:
                    teachers[tid] = teacher
        head_subjects = {r.subject for r in duty_relations if r.teacher_id == duty_cls.teacher_id and r.role == "subject_teacher"}
        initial_subjects = {p.subject.strip() for p in case_plans if p.subject.strip()}
        if is_head:
            student_scopes[(cls.id, student.id)] = dict(student_id=student.id, student_name=student.name,
                class_id=cls.id, class_name=cls.name, month_label=month_label,
                initial_required=not initial_subjects, total=0, written=0, unwritten=0)
        # 班主任可查看全班任课进度；任课老师仍仅查看本人职责，查看不授予代填权限。
        candidates = teachers.values() if is_head else [user]
        # 学科对应个人初评；德育是班主任固定职责，不依赖初评是否单独录入。
        head = teachers.get(duty_cls.teacher_id) if is_admin or is_supervision or context else user
        duties = [(MONTHLY_EVAL_ROLE_HEAD, "德育", head)] if is_head and head else []
        for teacher in candidates:
            teacher_relations = [r for r in duty_relations if r.teacher_id == teacher.id]
            assignment = _resolve_evaluation_role(duty_cls, teacher_relations, case, case_plans, head_subjects, teacher)
            if assignment and assignment[0] == MONTHLY_EVAL_ROLE_SUBJECT:
                # 每个初评科目单独一行；同一老师兼教也不合并成一个计数项。
                for subject in assignment[1].split("、"):
                    if subject in initial_subjects:
                        duties.append((assignment[0], subject, teacher))
        if is_head:
            by_subject = defaultdict(list)
            for duty in duties:
                by_subject[duty[1]].append(duty)
            # 一个初评科目只计一次；多人任课无法唯一确定时走下方待确认行。
            duties = [group[0] for group in by_subject.values() if len(group) == 1]
        for role, subject, teacher in duties:
            content = report.final_content if report and role == MONTHLY_EVAL_ROLE_HEAD else ""
            if report and role == MONTHLY_EVAL_ROLE_SUBJECT:
                content = next((e.content for e in report.evaluations if e.teacher_id == teacher.id and e.teacher_role == role
                                and subject in e.subject.split("、")), "")
                if not content and (report.input_snapshot or {}).get("transfer_origin"):
                    content = next((e.content for e in report.evaluations if e.teacher_role == role and subject in e.subject.split("、")), "")
            rows.append(dict(student_id=student.id, student_name=student.name, class_id=cls.id,
                             class_name=cls.name, month_label=month_label, teacher_role=role,
                             subject=subject, report_id=report.id if report else None,
                             teacher_id=teacher.id, teacher_name=teacher.name, can_edit=not (is_admin or is_supervision or context) and teacher.id == user.id,
                             writing_status="written" if content and content.strip() else "unwritten"))
        if is_head:
            # 初评科目即使尚未关联任课账号也必须可见；不能把未关联误报为全部已填。
            shown_subjects = {s.strip() for _, subject, _ in duties for s in subject.split("、")}
            for plan in case_plans:
                if not plan.subject.strip() or plan.subject.strip() in shown_subjects or plan.subject.strip() == "德育":
                    continue
                rows.append(dict(student_id=student.id, student_name=student.name, class_id=cls.id,
                                 class_name=cls.name, month_label=month_label, teacher_role=MONTHLY_EVAL_ROLE_SUBJECT,
                                 subject=plan.subject, report_id=report.id if report else None,
                                 teacher_id=None, teacher_name=plan.teacher_name.strip() or "待确认任课老师",
                                 can_edit=False, assignment_required=True, writing_status="unwritten"))
                shown_subjects.add(plan.subject.strip())
    written = sum(r["writing_status"] == "written" for r in rows)
    total = len(rows)
    selected = [r for r in rows if writing_status is None or r["writing_status"] == writing_status]
    # 先汇总完整职责，再筛选、按学生分页，避免兼任职责跨页导致漏算未填项。
    grouped = student_scopes
    for row in rows:
        key = (row["class_id"], row["student_id"])
        if key not in grouped:
            grouped[key] = {k: row[k] for k in ("student_id", "student_name", "class_id", "class_name", "month_label")}
            grouped[key].update(total=0, written=0, unwritten=0)
        grouped[key]["total"] += 1
        grouped[key][row["writing_status"]] += 1
    students = [s for s in grouped.values() if writing_status is None or s[writing_status] > 0]
    return dict(total=total, written=written, unwritten=total-written, filtered_total=len(selected),
                items=selected[offset:offset+limit] if view == "items" else [],
                students=students[offset:offset+limit] if view == "students" else [],
                student_total=len(students))


@router.get("/{report_id}", response_model=MonthlyReportOut)
def get_report(report_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = _report_access(db, report_id, user)
    return _enrich(r, db, user)

@router.put("/{report_id}/month", response_model=MonthlyReportOut)
def change_report_month(
    report_id: int, body: MonthlyReportMonthIn,
    db: Session = Depends(get_db), user: User = Depends(require_roles([ROLE_ADMIN])),
):
    period_start, period_end = _month_bounds(body.month_label)
    report = db.get(MonthlyReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="月度评定不存在")
    _require_unfrozen(db, report)
    # 与创建共用学生锁，再锁两个月的报告，避免与教师保存、重复移动互相覆盖。
    db.query(User).filter_by(id=report.student_id).with_for_update().first()
    report = db.query(MonthlyReport).filter_by(id=report_id).populate_existing().with_for_update().one()
    is_head = body.teacher_role == MONTHLY_EVAL_ROLE_HEAD
    evaluation = None
    if is_head:
        if body.subject != "德育" or not report.final_content.strip():
            raise HTTPException(status_code=409, detail="该科目尚未填写或已被调整，请刷新后重试")
        moving = [e for e in report.evaluations if e.teacher_role == MONTHLY_EVAL_ROLE_HEAD]
    else:
        evaluation = next((e for e in report.evaluations if e.teacher_role == MONTHLY_EVAL_ROLE_SUBJECT
                           and e.teacher_id == body.teacher_id and body.subject in e.subject.split("、")
                           and e.content.strip()), None)
        if evaluation is None:
            raise HTTPException(status_code=409, detail="该科目尚未填写或已被调整，请刷新后重试")
        moving = [evaluation]
    if report.month_label == body.month_label:
        return _enrich(report, db, user)
    target = db.query(MonthlyReport).filter_by(
        student_id=report.student_id, class_id=report.class_id, month_label=body.month_label,
    ).populate_existing().with_for_update().first()
    if target:
        # 同科或同教师已有内容均不自动合并，保护目标月份原有手写内容。
        conflict = bool(target.final_content.strip()) if is_head else any(
            e.teacher_role == MONTHLY_EVAL_ROLE_SUBJECT and body.subject in e.subject.split("、")
            for e in target.evaluations)
        conflict = conflict or any(e.teacher_id == m.teacher_id for e in target.evaluations for m in moving)
        if conflict:
            raise HTTPException(status_code=409, detail="目标月份已有该科目或该教师的评定，不能覆盖")
    else:
        target = MonthlyReport(student_id=report.student_id, class_id=report.class_id,
            student_case_id=report.student_case_id, month_label=body.month_label,
            period_start=period_start, period_end=period_end, status=report.status,
            published_at=report.published_at, prompt_version="manual_v1", final_content="")
        db.add(target)
        db.flush()
    old_month = report.month_label
    if is_head:
        target.final_content, report.final_content = report.final_content, ""
        target.reviewed_by = report.reviewed_by
        for item in moving:
            item.report_id = target.id
    else:
        remaining = [subject for subject in evaluation.subject.split("、") if subject != body.subject]
        if remaining:
            # 兼教老师历史上共用一条内容，拆出选中科目，原月其他科目继续保留。
            evaluation.subject = "、".join(remaining)
            target.evaluations.append(MonthlyReportEvaluation(teacher_id=evaluation.teacher_id,
                teacher_name=evaluation.teacher_name, teacher_role=evaluation.teacher_role,
                subject=body.subject, content=evaluation.content, created_at=evaluation.created_at))
        else:
            evaluation.report_id = target.id
    from app.services.student_case_service import audit
    audit(db, user.id, "monthly_report.month_changed", "monthly_report", report.id,
          report.student_case_id, {"from_month": old_month, "to_month": body.month_label,
          "subject": body.subject, "teacher_role": body.teacher_role,
          "teacher_id": body.teacher_id, "target_report_id": target.id})
    db.commit()
    db.refresh(target)
    return _enrich(target, db, user)


@router.put("/{report_id}", response_model=MonthlyReportOut)
def update_report(report_id: int, body: MonthlyReportUpdateIn, db: Session = Depends(get_db), user: User = Depends(_manager)):
    r = _report_access(db, report_id, user)
    _require_unfrozen(db, r)
    _require_manager(db, r.class_id, user)
    # 旧的失败/排队记录可由教师接手，保存后进入待发布状态。
    if r.status in (MONTHLY_STATUS_GENERATING, MONTHLY_STATUS_FAILED):
        r.status = MONTHLY_STATUS_GENERATED
        r.error_message = ""
    r.final_content = body.final_content.strip()
    r.reviewed_by = user.id
    for evaluation in r.evaluations:
        if evaluation.teacher_role == MONTHLY_EVAL_ROLE_HEAD and evaluation.teacher_id == user.id:
            evaluation.content = r.final_content
    if r.status == MONTHLY_STATUS_PUBLISHED:
        from datetime import datetime, timezone
        r.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(r)
    logger.info("monthly_updated report_id=%s teacher_id=%s", r.id, user.id)
    return _enrich(r, db, user)

@router.post("/{report_id}/publish", response_model=MonthlyReportOut)
def publish_report(report_id: int, db: Session = Depends(get_db), user: User = Depends(_manager)):
    r = _report_access(db, report_id, user)
    _require_unfrozen(db, r)
    if user.role != ROLE_ADMIN:
        _require_manager(db, r.class_id, user)
    if r.status != MONTHLY_STATUS_GENERATED:
        raise HTTPException(status_code=409, detail="只有待发布的月度评定可以发布")
    if not r.final_content.strip():
        raise HTTPException(status_code=409, detail="月度评定内容为空，不能发布")
    from datetime import datetime, timezone
    r.status = MONTHLY_STATUS_PUBLISHED
    r.reviewed_by = user.id
    r.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(r)
    logger.info("monthly_published report_id=%s teacher_id=%s", r.id, user.id)
    return _enrich(r, db, user)


@router.put("/{report_id}/evaluation", response_model=MonthlyReportOut)
def save_evaluation(
    report_id: int,
    body: MonthlyEvaluationSave,
    db: Session = Depends(get_db),
    user: User = Depends(_evaluator),
):
    # 同一份评定串行保存，避免重复点击或并发请求创建同一教师的重复评价。
    row = db.query(MonthlyReport).filter_by(id=report_id).with_for_update().first()
    if row is None:
        raise HTTPException(status_code=404, detail="月度评定不存在")
    _require_unfrozen(db, row)
    # 先校验可见性（任课老师仅所带班级），再校验评价身份。
    _report_access(db, report_id, user)
    role_subject = _evaluation_role(db, row, user)
    if role_subject is None:
        raise HTTPException(status_code=403, detail="仅本班班主任和所带学科老师可评价")
    role, subject = role_subject
    evaluation = db.query(MonthlyReportEvaluation).filter_by(report_id=row.id, teacher_id=user.id).first()
    if evaluation is None:
        evaluation = MonthlyReportEvaluation(report_id=row.id, teacher_id=user.id)
        db.add(evaluation)
    evaluation.teacher_name = user.name
    evaluation.teacher_role = role
    evaluation.subject = subject
    evaluation.content = body.content
    if role == MONTHLY_EVAL_ROLE_HEAD:
        # 班主任的德育评价与主报告正文保持同一来源。
        row.final_content = body.content
        row.reviewed_by = user.id
    db.commit()
    db.refresh(row)
    logger.info("monthly_evaluated report_id=%s teacher_id=%s role=%s", row.id, user.id, role)
    return _enrich(row, db, user)

@router.delete("/{report_id}")
def delete_report(report_id: int, db: Session = Depends(get_db), user: User = Depends(_manager)):
    r = _report_access(db, report_id, user)
    _require_unfrozen(db, r)
    if user.role != ROLE_ADMIN:
        _require_manager(db, r.class_id, user)
    db.delete(r)
    db.commit()
    return {"ok": True}
