"""班主任任务提醒、每日批量记录与阶段完成度 API。"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.case_points import CaseStageCompletion
from app.models.class_ import Class, ClassTeacher
from app.models.student_case import CaseTask, StudentCase, TaskCheckin
from app.models.user import (
    ROLE_ADMIN,
    ROLE_DEYU_DIRECTOR,
    ROLE_TEACHER,
    User,
)
from app.schemas.case_points import (
    BatchCheckinCreate,
    ReminderTaskItem,
    StageCompletionOut,
    TaskRemindersOut,
)
from app.schemas.student_case import TaskCheckinOut
from app.services.case_points_service import earned_of, recompute_stage_completion
from app.services.student_case_service import (
    audit,
    is_head_teacher,
    require_case_access,
    require_case_manager,
)

router = APIRouter(prefix="/student-cases", tags=["case-tasks"])
_head_teacher = require_roles([ROLE_TEACHER])
_staff = require_roles([ROLE_ADMIN, ROLE_DEYU_DIRECTOR, ROLE_TEACHER])


def _managed_class_ids(db: Session, user: User) -> set[int]:
    legacy = [row.id for row in db.query(Class).filter(Class.teacher_id == user.id).all()]
    relations = [
        row.class_id
        for row in db.query(ClassTeacher)
        .filter(ClassTeacher.teacher_id == user.id, ClassTeacher.role == "head_teacher")
        .all()
    ]
    return set(legacy + relations)


def _student_names(db: Session, student_ids: set[int]) -> dict[int, str]:
    from app.models.user import User as UserModel

    if not student_ids:
        return {}
    return {u.id: u.name for u in db.query(UserModel).filter(UserModel.id.in_(student_ids)).all()}


def _class_names(db: Session, class_ids: set[int]) -> dict[int, str]:
    if not class_ids:
        return {}
    return {c.id: c.name for c in db.query(Class).filter(Class.id.in_(class_ids)).all()}


@router.get("/tasks/reminders", response_model=TaskRemindersOut)
def task_reminders(
    class_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(_head_teacher),
):
    """班主任工作台待办：逾期任务 / 今日到期 / 今日未打卡（含学生任务安排与执行提醒）。"""
    managed = _managed_class_ids(db, user)
    if not managed:
        return TaskRemindersOut(date=date.today(), counts={"overdue": 0, "due_today": 0, "unlogged_today": 0})
    if class_id is not None:
        if class_id not in managed:
            raise HTTPException(status_code=403, detail="无权查看该班级任务提醒")
        class_ids = {class_id}
    else:
        class_ids = managed
    today = date.today()
    cases = db.query(StudentCase).filter(StudentCase.class_id.in_(class_ids)).all()
    if not cases:
        return TaskRemindersOut(date=today, counts={"overdue": 0, "due_today": 0, "unlogged_today": 0})
    case_by_id = {c.id: c for c in cases}
    tasks = (
        db.query(CaseTask)
        .filter(CaseTask.student_case_id.in_(list(case_by_id)))
        .order_by(CaseTask.due_on.asc())
        .all()
    )
    task_ids = [t.id for t in tasks]
    logged_today: set[int] = set()
    if task_ids:
        for row in db.query(TaskCheckin).filter(TaskCheckin.task_id.in_(task_ids)).all():
            log_date = row.log_date or (row.checked_in_at.date() if row.checked_in_at else None)
            if log_date == today:
                logged_today.add(row.task_id)
    student_names = _student_names(db, {c.student_id for c in cases})
    class_names = _class_names(db, class_ids)

    def item(task: CaseTask) -> ReminderTaskItem:
        case = case_by_id[task.student_case_id]
        overdue_days = (today - task.due_on).days if task.due_on < today else 0
        return ReminderTaskItem(
            task_id=task.id,
            case_id=case.id,
            student_id=case.student_id,
            student_name=student_names.get(case.student_id),
            class_id=case.class_id,
            class_name=class_names.get(case.class_id),
            subject=task.subject or "",
            title=task.title,
            cadence=task.cadence or "",
            starts_on=task.starts_on,
            due_on=task.due_on,
            status=task.status,
            version=task.version or 1,
            points=task.points or 0,
            overdue_days=overdue_days,
            logged_today=task.id in logged_today,
        )

    overdue, due_today, unlogged = [], [], []
    for task in tasks:
        if task.status in {"completed", "cancelled"}:
            continue
        if task.due_on < today:
            overdue.append(item(task))
        if task.due_on == today:
            due_today.append(item(task))
        # 执行提醒：今日应执行（已开始且未到期）但尚未每日记录
        if task.starts_on <= today <= task.due_on and task.id not in logged_today:
            unlogged.append(item(task))
    return TaskRemindersOut(
        date=today,
        overdue=overdue,
        due_today=due_today,
        unlogged_today=unlogged,
        counts={"overdue": len(overdue), "due_today": len(due_today), "unlogged_today": len(unlogged)},
    )


@router.post("/tasks/batch-checkin", response_model=list[TaskCheckinOut])
def batch_checkin(
    body: BatchCheckinCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_head_teacher),
):
    """班主任每日记录：一次提交多名学生/多任务当天的执行情况，自动折算积分并重算阶段完成度。"""
    log_date = body.log_date or date.today()
    seen_tasks: set[int] = set()
    results: list[TaskCheckin] = []
    affected_cases: dict[int, StudentCase] = {}
    for entry in body.items:
        if entry.task_id in seen_tasks:
            raise HTTPException(status_code=400, detail=f"任务 {entry.task_id} 在本次提交中重复")
        seen_tasks.add(entry.task_id)
        task = db.get(CaseTask, entry.task_id)
        if task is None:
            raise HTTPException(status_code=404, detail=f"任务 {entry.task_id} 不存在")
        case = require_case_access(db, task.student_case_id, user, write=True, subject=task.subject)
        require_case_manager(db, case, user)
        checkin = TaskCheckin(
            task_id=task.id,
            student_id=case.student_id,
            completion_rate=entry.completion_rate,
            self_check=entry.self_check or "",
            earned_points=earned_of(task.points or 0, entry.completion_rate),
            log_date=log_date,
        )
        db.add(checkin)
        if entry.completion_rate == 100:
            task.status = "completed"
        elif entry.completion_rate > 0:
            task.status = "in_progress"
        audit(
            db, user.id, "task.checkin", "task_checkin", checkin.id, case.id,
            {"rate": entry.completion_rate, "log_date": log_date.isoformat(), "batch": True},
        )
        results.append(checkin)
        affected_cases[case.id] = case
    db.flush()
    for case in affected_cases.values():
        recompute_stage_completion(db, case, recorded_by=user.id)
    db.commit()
    for row in results:
        db.refresh(row)
    return results


@router.get("/{case_id}/stage-completions", response_model=list[StageCompletionOut])
def list_stage_completions(
    case_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """查看该总案每个阶段（版本）的任务完成度记录。"""
    require_case_access(db, case_id, user)
    return (
        db.query(CaseStageCompletion)
        .filter_by(student_case_id=case_id)
        .order_by(CaseStageCompletion.version.asc())
        .all()
    )


@router.post("/{case_id}/stage-completions/rebuild", response_model=StageCompletionOut)
def rebuild_stage_completion(
    case_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(_staff),
):
    """从任务与打卡重算当前阶段完成度（每日记录后一般自动更新，此接口用于手动校准）。"""
    case = require_case_access(db, case_id, user, write=True)
    require_case_manager(db, case, user)
    row = recompute_stage_completion(db, case, recorded_by=user.id)
    audit(db, user.id, "stage.rebuild", "case_stage_completion", row.id, case.id, {"version": case.version})
    db.commit()
    db.refresh(row)
    return row
