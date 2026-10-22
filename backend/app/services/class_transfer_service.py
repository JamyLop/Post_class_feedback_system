"""调班预览与原子交接。历史业务记录保留归属，当前责任单独转交。"""
import calendar
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder

from app.models.class_ import Class, ClassStudent, ClassTeacher
from app.models.class_transfer import ClassTransferBatch, ClassTransferItem
from app.models.monthly_report import MonthlyReport, MONTHLY_STATUS_PUBLISHED
from app.models.student_case import CaseCycle, CaseReview, StudentCase, SubjectPlan
from app.models.user import User, ROLE_STUDENT, ROLE_TEACHER, ROLE_SUBJECT_TEACHER
from app.models.weekly_score import WeeklyTestScore
from app.services.student_case_service import audit, snapshot_payload

SCHOOL_TZ = ZoneInfo("Asia/Shanghai")


def school_now():
    return datetime.now(timezone.utc)


def digest(value):
    return hashlib.sha256(json.dumps(jsonable_encoder(value), sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def same_roster_scope(a, b):
    # 只排斥同一教学组织；全年班调班不能删除另行参加的1V1/短期课程班。
    return (a.school_year, a.education_stage, a.grade, a.class_type, a.short_term_type) == (
        b.school_year, b.education_stage, b.grade, b.class_type, b.short_term_type)


def assert_can_enroll(db, student_id, cls):
    other = db.query(Class).join(ClassStudent, ClassStudent.class_id == Class.id).filter(
        ClassStudent.student_id == student_id, Class.id != cls.id).all()
    if any(same_roster_scope(c, cls) for c in other):
        raise HTTPException(409, "学生已在同类班级，请由德育主任或管理员使用批量调班")


def _columns(row):
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


def build_preview(db, body):
    now = school_now().astimezone(SCHOOL_TZ)
    classes = {c.id: c for c in db.query(Class).all()}
    names = [r.student_username for r in body.rows]
    users = {u.username: u for u in db.query(User).filter(User.username.in_(names)).all()}
    duplicates = Counter(names)
    results, state, counts = [], [], Counter()
    for number, row in enumerate(body.rows, 1):
        errors, assignments = [], []
        student = users.get(row.student_username)
        target = classes.get(row.target_class_id)
        source = None
        cases, memberships, reports, scores = [], [], [], []
        if duplicates[row.student_username] > 1:
            errors.append("同一学生在本批次重复出现")
        if student is None or student.role != ROLE_STUDENT or student.status != "active":
            errors.append("学号不存在或不是启用的学生账号")
        if student and row.student_name and student.name != row.student_name:
            errors.append("姓名与学号不匹配")
        if target is None:
            errors.append("目标班级不存在")
        elif (head := db.get(User, target.teacher_id)) is None or head.role != ROLE_TEACHER or head.status != "active":
            errors.append("目标班级尚未配置启用的班主任")
        if student and target:
            memberships = db.query(ClassStudent).filter_by(student_id=student.id).order_by(ClassStudent.class_id).all()
            candidates = [classes[m.class_id] for m in memberships if same_roster_scope(classes[m.class_id], target)]
            source = classes.get(row.source_class_id) if row.source_class_id else candidates[0] if len(candidates) == 1 else None
            if source is None:
                errors.append("无法唯一确定原班级，请明确原班级")
            elif not any(m.class_id == source.id for m in memberships):
                errors.append("学生已不属于原班级，请刷新名单")
            elif source.id == target.id:
                errors.append("原班级与目标班级相同")
            elif not same_roster_scope(source, target):
                errors.append("仅支持同学年、同学段、同年级、同班型之间调班")
            if source and any(c.id not in {source.id} for c in candidates):
                errors.append("存在重复在班关系，请先核对学生名单")
        snapshots = []
        relations, score_subjects = [], []
        if student and source and target:
            cases = db.query(StudentCase).join(CaseCycle, CaseCycle.id == StudentCase.cycle_id).filter(
                StudentCase.student_id == student.id, StudentCase.class_id == source.id,
                StudentCase.status != "archived", CaseCycle.is_active.is_(True),
                CaseCycle.school_year == source.school_year).order_by(StudentCase.id).all()
            other_cases = db.query(StudentCase).join(CaseCycle, CaseCycle.id == StudentCase.cycle_id).filter(
                StudentCase.student_id == student.id, StudentCase.class_id.in_([source.id, target.id]),
                StudentCase.status != "archived", CaseCycle.is_active.is_(True),
                CaseCycle.school_year != source.school_year).first()
            if other_cases:
                errors.append("存在学年不一致的活动档案，请先核对")
            relations = db.query(ClassTeacher).filter(ClassTeacher.class_id.in_([source.id, target.id])).order_by(ClassTeacher.id).all()
            all_plans = db.query(SubjectPlan).filter(SubjectPlan.student_case_id.in_([c.id for c in cases])).order_by(SubjectPlan.id).all()
            for subject in sorted({p.subject for p in all_plans}):
                if subject == "德育":
                    assignments.append(dict(subject=subject, teacher_id=target.teacher_id, options=[]))
                    continue
                ids = {r.teacher_id for r in relations if r.class_id == target.id and r.role == "subject_teacher" and r.subject == subject}
                teachers = db.query(User).filter(User.id.in_(ids), User.status == "active",
                    User.role.in_([ROLE_TEACHER, ROLE_SUBJECT_TEACHER])).order_by(User.id).all()
                selected = row.subject_teachers.get(subject) or (teachers[0].id if len(teachers) == 1 else None)
                if selected not in {t.id for t in teachers}:
                    errors.append(f"请为{subject}指定目标班级的任课老师")
                    selected = None
                assignments.append(dict(subject=subject, teacher_id=selected,
                    options=[dict(id=t.id, name=t.name) for t in teachers]))
            snapshots = [snapshot_payload(db, c) for c in cases]
            reports = db.query(MonthlyReport).filter(MonthlyReport.student_id == student.id,
                MonthlyReport.class_id.in_([source.id, target.id])).order_by(MonthlyReport.id).all()
            source_reports = [r for r in reports if r.class_id == source.id and r.month_label >= now.strftime("%Y-%m")]
            for report in source_reports:
                if any(r.class_id == target.id and r.month_label == report.month_label for r in reports):
                    errors.append(f"{report.month_label}目标班已有月评，不能自动合并")
            scores = db.query(WeeklyTestScore).filter_by(student_id=student.id, class_id=source.id).order_by(WeeklyTestScore.id).all()
            latest = db.query(StudentCase).filter_by(student_id=student.id, class_id=source.id).filter(
                StudentCase.status != "archived").order_by(StudentCase.id.desc()).first()
            if latest:
                score_subjects = sorted({p.subject.strip() for p in db.query(SubjectPlan).filter_by(student_case_id=latest.id)
                    if p.subject.strip() and p.subject.strip() != "德育"})
        info = dict(row_number=number, student_id=student.id if student else None,
            student_username=row.student_username, student_name=student.name if student else row.student_name,
            source_class_id=source.id if source else row.source_class_id,
            source_class_name=source.name if source else "", target_class_id=row.target_class_id,
            target_class_name=target.name if target else "", case_count=len(cases), assignments=assignments, errors=errors)
        results.append(info)
        state.append(dict(row=row.model_dump(), info=info,
            student={k: v for k, v in _columns(student).items() if k != "password_hash"} if student else None,
            source=_columns(source) if source else None, target=_columns(target) if target else None,
            memberships=[_columns(m) for m in memberships], snapshots=snapshots,
            relations=[_columns(r) for r in relations],
            reports=[dict(data=_columns(r), evaluations=[_columns(e) for e in r.evaluations]) for r in reports],
            scores=[_columns(s) for s in scores], score_subjects=score_subjects))
        if not errors:
            counts[source.id] -= 1
            counts[target.id] += 1
    summary = []
    for class_id in sorted(counts):
        before = db.query(ClassStudent).filter_by(class_id=class_id).count()
        summary.append(dict(class_id=class_id, class_name=classes[class_id].name, before=before, after=before + counts[class_id]))
    return dict(valid=all(not r["errors"] for r in results), rows=results, classes=summary,
        preview_token=digest(dict(month=now.strftime("%Y-%m"), state=state, summary=summary))), state


def commit_transfer(db, body, actor):
    payload_hash = digest(dict(rows=[r.model_dump() for r in body.rows], reason=body.reason))
    # 学生锁使两个管理员同时调同一学生、重试同一批次时串行；全部校验通过后才写入。
    names = sorted({r.student_username for r in body.rows})
    db.query(User).filter(User.username.in_(names)).order_by(User.id).with_for_update().all()
    existing = db.query(ClassTransferBatch).filter_by(request_id=body.request_id).first()
    if existing:
        if existing.payload_hash != payload_hash or existing.actor_id != actor.id:
            raise HTTPException(409, "该提交编号已使用，请重新预览")
        return batch_out(db, existing)
    class_ids = {r.target_class_id for r in body.rows} | {
        m.class_id for m in db.query(ClassStudent).join(User, User.id == ClassStudent.student_id).filter(User.username.in_(names))}
    db.query(Class).filter(Class.id.in_(class_ids)).order_by(Class.id).with_for_update().all()
    student_ids = [u.id for u in db.query(User).filter(User.username.in_(names))]
    cases = db.query(StudentCase).filter(StudentCase.student_id.in_(student_ids)).order_by(StudentCase.id).with_for_update().all()
    db.query(SubjectPlan).filter(SubjectPlan.student_case_id.in_([c.id for c in cases])).order_by(SubjectPlan.id).with_for_update().all()
    db.query(MonthlyReport).filter(MonthlyReport.student_id.in_(student_ids)).order_by(MonthlyReport.id).with_for_update().all()
    db.expire_all()
    preview, states = build_preview(db, body)
    if not preview["valid"]:
        raise HTTPException(409, "名单或任课安排已变化，请重新预览并修正")
    if preview["preview_token"] != body.preview_token:
        raise HTTPException(409, "预览后数据已变化，请重新预览再提交")
    now = school_now()
    month = now.astimezone(SCHOOL_TZ).strftime("%Y-%m")
    batch = ClassTransferBatch(request_id=body.request_id, payload_hash=payload_hash, reason=body.reason,
        actor_id=actor.id, actor_name=actor.name, created_at=now)
    db.add(batch)
    db.flush()
    for state in states:
        info = state["info"]
        sid, source_id, target_id = info["student_id"], info["source_class_id"], info["target_class_id"]
        target = db.get(Class, target_id)
        membership = db.query(ClassStudent).filter_by(student_id=sid, class_id=source_id).one()
        joined_at = membership.joined_at
        db.delete(membership)
        db.add(ClassStudent(student_id=sid, class_id=target_id, joined_at=now))
        assignment = {a["subject"]: a["teacher_id"] for a in info["assignments"]}
        for snapshot in state["snapshots"]:
            case = db.get(StudentCase, snapshot["case"]["id"])
            case.class_id, case.owner_teacher_id = target_id, target.teacher_id
            for plan in db.query(SubjectPlan).filter_by(student_case_id=case.id):
                plan.teacher_id = assignment[plan.subject]
                plan.teacher_name = db.get(User, plan.teacher_id).name
            for review in db.query(CaseReview).filter(CaseReview.student_case_id == case.id,
                CaseReview.workflow_status.in_(["open", "resubmitted"])):
                review.assigned_to = target.teacher_id
            audit(db, actor.id, "case.class_transferred", "student_case", case.id, case.id,
                dict(batch_id=batch.id, source_class_id=source_id, target_class_id=target_id,
                     previous_owner=snapshot["case"]["owner_teacher_id"], assignments=assignment))
        # 考试时的选科与当时班级一起保留，防止移动档案后旧成绩从排名中消失。
        subjects = state["score_subjects"]
        for score in db.query(WeeklyTestScore).filter_by(student_id=sid, class_id=source_id):
            if score.study_subjects_snapshot is None:
                score.study_subjects_snapshot = subjects
        moved_reports = []
        for report in db.query(MonthlyReport).filter_by(student_id=sid, class_id=source_id):
            if report.month_label >= month and report.status != MONTHLY_STATUS_PUBLISHED:
                report.input_snapshot = {**(report.input_snapshot or {}), "transfer_origin": {
                    "class_id": source_id, "batch_id": batch.id, "month_label": report.month_label}}
                report.class_id = target_id
                moved_reports.append(report.id)
        detail = jsonable_encoder(dict(source_joined_at=joined_at, cases=state["snapshots"],
            source=state["source"], relations=state["relations"], reports=state["reports"],
            assignments=assignment, moved_report_ids=moved_reports))
        db.add(ClassTransferItem(batch_id=batch.id, student_id=sid, student_username=info["student_username"],
            student_name=info["student_name"], source_class_id=source_id, target_class_id=target_id,
            source_class_name=info["source_class_name"], target_class_name=info["target_class_name"],
            effective_at=now, detail=detail))
    audit(db, actor.id, "class.transfer_batch", "class_transfer_batch", batch.id,
          detail=dict(student_count=len(states), reason=body.reason))
    db.commit()
    return batch_out(db, batch)


def batch_out(db, batch):
    items = db.query(ClassTransferItem).filter_by(batch_id=batch.id).order_by(ClassTransferItem.id).all()
    return dict(id=batch.id, request_id=batch.request_id, reason=batch.reason, actor_name=batch.actor_name,
        created_at=batch.created_at, student_count=len(items), items=[dict(
            student_id=i.student_id, student_username=i.student_username, student_name=i.student_name,
            source_class_id=i.source_class_id, target_class_id=i.target_class_id,
            source_class_name=i.source_class_name, target_class_name=i.target_class_name,
            effective_at=i.effective_at) for i in items])


def historical_roster(db, month_label, class_ids, student_id=None):
    """还原月末名单；只回放调班事件，不把旧班关系留在当前名单中。"""
    year, month = map(int, month_label.split("-"))
    boundary = datetime(year, month, calendar.monthrange(year, month)[1], 23, 59, 59, 999999, tzinfo=SCHOOL_TZ)
    return roster_at(db, boundary, class_ids, student_id)


def roster_at(db, boundary, class_ids, student_id=None):
    """月评与积分报表共用周期末名单，周报同样能跨调班日期还原。"""
    members = {(m.class_id, m.student_id): m for m in db.query(ClassStudent)}
    events = db.query(ClassTransferItem).filter(ClassTransferItem.effective_at > boundary).order_by(
        ClassTransferItem.effective_at.desc(), ClassTransferItem.id.desc()).all()
    contexts = {}
    for event in events:
        members.pop((event.target_class_id, event.student_id), None)
        key = event.source_class_id, event.student_id
        joined_at = datetime.fromisoformat(event.detail["source_joined_at"])
        if joined_at.tzinfo is None:
            joined_at = joined_at.replace(tzinfo=timezone.utc)
        members[key] = SimpleNamespace(class_id=event.source_class_id, student_id=event.student_id,
            joined_at=joined_at)
        contexts[key] = event.detail
    # 存量导入名单的 joined_at 不是可靠入学日期；只按已留痕的调班还原，不反推入学月份。
    selected = [m for (cid, sid), m in members.items() if cid in class_ids and (student_id is None or sid == student_id)]
    users = {u.id: u for u in db.query(User).filter(User.id.in_({m.student_id for m in selected}), User.role == ROLE_STUDENT)}
    return [(m, users[m.student_id]) for m in sorted(selected, key=lambda m: (m.class_id, m.student_id)) if m.student_id in users], contexts


def current_head_student_ids(db, user):
    cls_ids = {c.id for c in db.query(Class).filter_by(teacher_id=user.id)} | {
        r.class_id for r in db.query(ClassTeacher).filter_by(teacher_id=user.id, role="head_teacher")}
    return db.query(ClassStudent.student_id).filter(ClassStudent.class_id.in_(cls_ids)).scalar_subquery()


def can_read_transferred_history(db, user, student_id, source_class_id):
    if user.role != ROLE_TEACHER:
        return False
    return db.query(ClassTransferItem.id).filter_by(student_id=student_id, source_class_id=source_class_id).first() is not None and db.query(
        ClassStudent).filter(ClassStudent.student_id == student_id, ClassStudent.student_id.in_(current_head_student_ids(db, user))).first() is not None


def frozen_report_context(db, report):
    """转班前已经发布或属于过去月份的评定，保留原作者且不再编辑。"""
    if not report.id:
        return None
    for event in db.query(ClassTransferItem).filter_by(student_id=report.student_id).order_by(ClassTransferItem.id.desc()):
        for saved in event.detail["reports"]:
            data = saved["data"]
            if data["id"] == report.id and (data["status"] == MONTHLY_STATUS_PUBLISHED or data["month_label"] < event.effective_at.astimezone(SCHOOL_TZ).strftime("%Y-%m")):
                return event.detail
    return None
