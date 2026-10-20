"""月考成绩册：按学生本人入学评定科目，在已授权数据内计算同口径排名。"""

from collections import defaultdict
from decimal import Decimal

from app.models.class_ import Class, ClassTeacher
from app.models.student_case import StudentCase, SubjectPlan
from app.models.user import ROLE_ADMIN, ROLE_DEYU_DIRECTOR, User
from app.models.weekly_score import WeeklyTestScore


def _rank(entries):
    """竞赛排名：同分并列，例如 1、1、3。"""
    previous = None
    rank = 0
    for position, (value, target, field) in enumerate(sorted(entries, key=lambda item: item[0], reverse=True), 1):
        if value != previous:
            rank = position
        target[field] = rank
        previous = value


def build_overview(db, user, query, exam_month, class_id, grade, subject, keyword, limit, offset):
    query = query.filter(WeeklyTestScore.exam_month.is_not(None), WeeklyTestScore.exam_month != "")
    months = [row[0] for row in query.with_entities(WeeklyTestScore.exam_month).distinct()
              .order_by(WeeklyTestScore.exam_month.desc()).all()]
    month = exam_month or (months[0] if months else None)
    records = query.filter(WeeklyTestScore.exam_month == month).all() if month else []
    class_ids = {record.class_id for record in records}
    classes = {cls.id: cls for cls in db.query(Class).filter(Class.id.in_(class_ids)).all()} if class_ids else {}
    student_ids = {record.student_id for record in records}
    students = {student.id: student for student in db.query(User).filter(User.id.in_(student_ids)).all()} if student_ids else {}
    global_access = user.role in (ROLE_ADMIN, ROLE_DEYU_DIRECTOR)
    head_ids = {cls.id for cls in classes.values() if cls.teacher_id == user.id}
    head_ids.update(row.class_id for row in db.query(ClassTeacher).filter_by(teacher_id=user.id, role="head_teacher").all())

    # 与入学评定、月度评定使用同一来源；同班学生的选科不能互相补齐。
    latest_cases = {}
    for case in db.query(StudentCase.id, StudentCase.class_id, StudentCase.student_id).filter(
        StudentCase.class_id.in_(class_ids), StudentCase.student_id.in_(student_ids),
        StudentCase.status != "archived",
    ).order_by(StudentCase.id.desc()).all():
        latest_cases.setdefault((case.class_id, case.student_id), case.id)
    case_subjects = defaultdict(set)
    for plan in db.query(SubjectPlan.student_case_id, SubjectPlan.subject).filter(
        SubjectPlan.student_case_id.in_(set(latest_cases.values())),
    ).all():
        name = plan.subject.strip()
        if name and name != "德育":
            case_subjects[plan.student_case_id].add(name)
    expected = {key: case_subjects[case_id] for key, case_id in latest_cases.items()}

    rows = {}
    for record in records:
        cls = classes[record.class_id]
        key = (record.class_id, record.student_id)
        if key not in rows:
            rows[key] = dict(class_id=cls.id, class_name=cls.name, grade=cls.grade,
                             student_id=record.student_id, student_name=students[record.student_id].name,
                             scores={}, total_score=None, total_max_score=None, complete=False,
                             can_view_total=global_access or cls.id in head_ids,
                             study_subjects=[], missing_subjects=[], class_rank=None, scope_rank=None)
        name = record.subject.strip()
        # 初评之外的历史录入保留在原记录中，不进入本人当前学习科目的成绩册。
        if name not in expected.get(key, set()):
            continue
        rows[key]["scores"][name] = dict(score=record.score, max_score=record.max_score,
                                                  class_rank=None, scope_rank=None)

    class_groups = defaultdict(list)
    scope_groups = defaultdict(list)
    for row in rows.values():
        scores = row["scores"]
        for name, cell in scores.items():
            class_groups[(row["class_id"], name, cell["max_score"])].append((cell["score"], cell, "class_rank"))
            scope_groups[(row["grade"], name, cell["max_score"])].append((cell["score"], cell, "scope_rank"))
        if not row["can_view_total"]:
            # 任课老师的返回中也不能带出该生其他初评科目。
            row["study_subjects"] = sorted(scores)
            continue
        study_subjects = expected.get((row["class_id"], row["student_id"]), set())
        row["study_subjects"] = sorted(study_subjects)
        row["missing_subjects"] = sorted(study_subjects - scores.keys())
        row["complete"] = bool(study_subjects) and not row["missing_subjects"]
        # 尚未建立初评时不猜测学习科目，也不将没有匹配科目的记录误算为0分。
        if not scores:
            continue
        row["total_score"] = float(sum((Decimal(str(cell["score"])) for cell in scores.values()), Decimal(0)))
        row["total_max_score"] = float(sum((Decimal(str(cell["max_score"])) for cell in scores.values()), Decimal(0)))
        # 按本人初评科目判断可比性，不同选科或满分配置分别排名。
        if row["complete"]:
            profile = tuple(sorted((name, cell["max_score"]) for name, cell in scores.items()))
            class_groups[(row["class_id"], "total", profile)].append((row["total_score"], row, "class_rank"))
            scope_groups[(row["grade"], "total", profile)].append((row["total_score"], row, "scope_rank"))
    for group in (*class_groups.values(), *scope_groups.values()):
        _rank(group)

    visible = [row for row in rows.values() if row["can_view_total"] or row["scores"]]
    grades = sorted({row["grade"] for row in visible})
    if class_id is not None:
        visible = [row for row in visible if row["class_id"] == class_id]
    if grade:
        visible = [row for row in visible if row["grade"] == grade]
    subjects = sorted({name for row in visible for name in row["study_subjects"]})
    if subject:
        visible = [row for row in visible if subject in row["scores"]]
    if keyword.strip():
        visible = [row for row in visible if keyword.strip().casefold() in row["student_name"].casefold()]

    def sort_key(row):
        value = row["scores"].get(subject, {}).get("score") if subject else row["total_score"] if row["complete"] else None
        return (value is None, -(value or 0), row["class_id"], row["student_id"])

    visible.sort(key=sort_key)
    return dict(exam_month=month, months=months, grades=grades, subjects=subjects,
                total=len(visible), items=visible[offset:offset + limit],
                has_total_access=any(row["can_view_total"] for row in visible),
                ranking_note="所学科目与本人入学评定一致；总分汇总本人已录入的初评科目成绩。本人初评科目成绩全部录入后，按同月、同年级、同科目及满分比较总分排名；同分并列。")
