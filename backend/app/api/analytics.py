"""阶段 5：学情分析 API。

- 学生知识点掌握度 / 薄弱点 TOP N / 成绩趋势
- 单次作业分析
- 班级学情

权限：学生仅能看自己的数据；教师仅能看自己班级/作业的数据；admin 全量。
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.analytics.service import (
    ensure_student_stats,
    get_assignment_analysis,
    get_class_analytics,
    get_student_knowledge_stats,
    get_student_learning_trend,
    get_student_repeated_errors,
    get_student_weak_points,
    recompute_student_stats,
)
from app.auth.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.assignment import Assignment
from app.models.class_ import Class, ClassStudent
from app.models.submission import Submission
from app.models.user import ROLE_ADMIN, ROLE_STUDENT, ROLE_TEACHER, User
from app.schemas.analytics import (
    AssignmentAnalysisOut,
    ClassAnalyticsOut,
    KnowledgeStatOut,
    LearningTrendOut,
    ErrorTypeCountOut,
    WeakPointOut,
)

router = APIRouter(tags=["analytics"])

_manager = require_roles([ROLE_ADMIN, ROLE_TEACHER])


def _student_exists(db: Session, student_id: int) -> User:
    """校验学生存在且角色正确，否则 404。"""
    student = db.get(User, student_id)
    if student is None or student.role != ROLE_STUDENT:
        raise HTTPException(status_code=404, detail="学生不存在")
    return student


def _student_class_scope(
    db: Session,
    student: User,
    user: User,
    class_id: int | None,
) -> int | None:
    """返回教师/admin请求的班级范围；学生本人返回全量范围。"""
    if user.role == ROLE_STUDENT:
        if student.id != user.id:
            raise HTTPException(status_code=403, detail="无权查看该学生学情")
        return None
    if user.role == ROLE_TEACHER and class_id is None:
        raise HTTPException(status_code=400, detail="教师查看学生学情时必须指定班级")
    if class_id is None:
        return None
    cls = db.get(Class, class_id)
    if cls is None:
        raise HTTPException(status_code=404, detail="班级不存在")
    if user.role != ROLE_ADMIN and cls.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="无权查看该班级学情")
    # 目标学生必须属于该班级
    membership = (
        db.query(ClassStudent)
        .filter(
            ClassStudent.class_id == class_id,
            ClassStudent.student_id == student.id,
        )
        .first()
    )
    if membership is None:
        raise HTTPException(status_code=403, detail="无权查看该学生学情")
    return class_id


def _get_class(db: Session, class_id: int) -> Class:
    cls = db.get(Class, class_id)
    if cls is None:
        raise HTTPException(status_code=404, detail="班级不存在")
    return cls


def _can_view_class(db: Session, cls: Class, user: User) -> None:
    """班级学情查看权限：admin 全量，教师仅限自己负责的班级。"""
    if user.role == ROLE_ADMIN:
        return
    if cls.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="无权查看该班级学情")


def _get_class_student_ids(db: Session, cls: Class) -> list[int]:
    """返回班级内全部学生 id 列表。"""
    return [
        r[0]
        for r in db.query(ClassStudent.student_id)
        .filter(ClassStudent.class_id == cls.id)
        .all()
    ]


def _get_assignment(db: Session, assignment_id: int) -> Assignment:
    a = db.get(Assignment, assignment_id)
    if a is None:
        raise HTTPException(status_code=404, detail="作业不存在")
    return a


def _can_view_assignment(db: Session, assignment: Assignment, user: User) -> None:
    """作业分析查看权限：admin 全量，教师仅限自己布置的作业。"""
    if user.role == ROLE_ADMIN:
        return
    if assignment.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="无权查看该作业分析")


@router.get(
    "/students/{student_id}/knowledge-stats",
    response_model=list[KnowledgeStatOut],
)
def student_knowledge_stats(
    student_id: int,
    class_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """学生知识点掌握度列表。"""
    student = _student_exists(db, student_id)
    scope = _student_class_scope(db, student, user, class_id)
    ensure_student_stats(db, student_id)
    return get_student_knowledge_stats(db, student_id, scope)


@router.get(
    "/students/{student_id}/weak-points",
    response_model=list[WeakPointOut],
)
def student_weak_points(
    student_id: int,
    top_n: int = Query(default=5, ge=1, le=50),
    min_records: int = Query(default=1, ge=0),
    class_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """学生薄弱知识点 TOP N。"""
    student = _student_exists(db, student_id)
    scope = _student_class_scope(db, student, user, class_id)
    ensure_student_stats(db, student_id)
    return get_student_weak_points(db, student_id, top_n, min_records, scope)


@router.get(
    "/students/{student_id}/learning-trend",
    response_model=LearningTrendOut,
)
def student_learning_trend(
    student_id: int,
    class_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """学生成绩趋势（按时间排序的作业得分百分比）。"""
    student = _student_exists(db, student_id)
    scope = _student_class_scope(db, student, user, class_id)
    return get_student_learning_trend(db, student_id, scope)


@router.get(
    "/students/{student_id}/repeated-errors",
    response_model=list[ErrorTypeCountOut],
)
def student_repeated_errors(
    student_id: int,
    top_n: int = Query(default=10, ge=1, le=50),
    min_count: int = Query(default=2, ge=1),
    class_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """学生重复错误统计（按错误类型聚合）。"""
    student = _student_exists(db, student_id)
    scope = _student_class_scope(db, student, user, class_id)
    return get_student_repeated_errors(db, student_id, top_n, min_count, scope)


@router.post(
    "/students/{student_id}/knowledge-stats/recompute",
    response_model=list[KnowledgeStatOut],
)
def recompute_student_stats_api(
    student_id: int,
    class_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(_manager),
):
    """教师手动重算某学生的掌握度（兜底：迁移历史数据 / 修正异常）。"""
    student = _student_exists(db, student_id)
    scope = _student_class_scope(db, student, user, class_id)
    recompute_student_stats(db, student_id)
    db.commit()
    return get_student_knowledge_stats(db, student_id, scope)


@router.get(
    "/assignments/{assignment_id}/analysis",
    response_model=AssignmentAnalysisOut,
)
def assignment_analysis(
    assignment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(_manager),
):
    """单次作业整体分析。"""
    a = _get_assignment(db, assignment_id)
    _can_view_assignment(db, a, user)
    return get_assignment_analysis(db, assignment_id)


@router.get(
    "/classes/{class_id}/analytics",
    response_model=ClassAnalyticsOut,
)
def class_analytics(
    class_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(_manager),
):
    """班级整体学情分析。"""
    cls = _get_class(db, class_id)
    _can_view_class(db, cls, user)
    student_ids = _get_class_student_ids(db, cls)
    return get_class_analytics(db, class_id, student_ids)
