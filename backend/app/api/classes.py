"""班级管理 API：班级 CRUD 与学生名单维护。"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_roles
from app.core.database import get_db
from app.core.pagination import MAX_LIMIT
from app.models.class_ import Class, ClassStudent, StudentConsultant
from app.models.user import ROLE_ADMIN, ROLE_CONSULTANT, ROLE_DEYU_DIRECTOR, ROLE_STUDENT, ROLE_SUBJECT_TEACHER, ROLE_TEACHER, User
from app.core.security import hash_password

from app.schemas.class_ import (
    ClassCreate,
    ClassOut,
    ClassStudentOut,
    ClassUpdate,
    StudentAdd,
    StudentCreateAndEnroll,
    validate_class_category,
)

router = APIRouter(prefix="/classes", tags=["classes"])

# 班级本身由德育主任（校长兼容）新建并分配班主任；班主任仅负责录入班级学生信息。
_class_manager = require_roles([ROLE_ADMIN, ROLE_DEYU_DIRECTOR])
# 班级学生名单维护：班主任录入，德育主任/校长可协同。
_student_manager = require_roles([ROLE_ADMIN, ROLE_DEYU_DIRECTOR, ROLE_TEACHER])


def _classes_out(db: Session, classes: list[Class]) -> list[dict]:
    """批量回填班主任姓名，避免 N+1 查询。"""
    teacher_ids = {c.teacher_id for c in classes if c.teacher_id}
    names: dict[int, str] = {}
    if teacher_ids:
        for u in db.query(User).filter(User.id.in_(teacher_ids)).all():
            names[u.id] = u.name
    result = []
    for c in classes:
        data = ClassOut.model_validate(c).model_dump()
        data["teacher_name"] = names.get(c.teacher_id, "")
        result.append(data)
    return result


def _check_class_owner(db: Session, class_id: int, user: User) -> Class:
    """校验班级存在且当前用户有权操作（教师仅限自己的班级，任课老师仅限所带学科班级）。

    德育主任为全局督查角色，允许只读单个班级及学生名单；写接口另有
    _manager（仅 admin/teacher）把关，因此在此放行不会扩大写权限。
    """
    cls = db.get(Class, class_id)
    if cls is None:
        raise HTTPException(status_code=404, detail="班级不存在")
    if user.role in (ROLE_ADMIN, ROLE_DEYU_DIRECTOR):
        return cls
    if cls.teacher_id == user.id:
        return cls
    from app.models.class_ import ClassTeacher

    if db.query(ClassTeacher).filter_by(class_id=class_id, teacher_id=user.id).first():
        return cls
    raise HTTPException(status_code=403, detail="无权操作该班级")


@router.post("", response_model=ClassOut)
def create_class(
    body: ClassCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_class_manager),
):
    """新建班级（德育主任操作，分配给班主任；校长兼容）。

    body.teacher_id 为分配的班主任ID；德育主任必须传入，管理员不传时默认归自己
    （若自己不是班主任则必须传入）。
    """
    data = body.model_dump(exclude={"teacher_id"})
    teacher_id = body.teacher_id
    if teacher_id is None:
        # 兼容：班主任历史调用不传 teacher_id 时归自己；德育主任/校长必须显式分配
        if user.role == ROLE_TEACHER:
            teacher_id = user.id
        else:
            raise HTTPException(status_code=422, detail="请指定分配的班主任（teacher_id）")
    teacher = db.get(User, teacher_id)
    if teacher is None or teacher.role != ROLE_TEACHER:
        raise HTTPException(status_code=400, detail="所选账号不是班主任")
    cls = Class(**data, teacher_id=teacher.id)
    db.add(cls)
    db.commit()
    db.refresh(cls)
    return _classes_out(db, [cls])[0]


@router.get("", response_model=list[ClassOut])
def list_classes(
    limit: int = Query(default=200, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """班级列表：admin/德育主任全部、教师自己的、任课老师所带学科班级、咨询老师关联学生所在班级、学生所在班级。"""
    from app.models.user import ROLE_DEYU_DIRECTOR

    if user.role in (ROLE_ADMIN, ROLE_DEYU_DIRECTOR):
        return _classes_out(db, db.query(Class).order_by(Class.id.desc()).offset(offset).limit(limit).all())
    if user.role == ROLE_CONSULTANT:
        student_ids = [r.student_id for r in db.query(StudentConsultant).filter_by(consultant_id=user.id).all()]
        if not student_ids:
            return []
        class_ids = [r.class_id for r in db.query(ClassStudent).filter(ClassStudent.student_id.in_(student_ids)).all()]
        if not class_ids:
            return []
        return _classes_out(db, db.query(Class).filter(Class.id.in_(set(class_ids))).order_by(Class.id.desc()).offset(offset).limit(limit).all())
    if user.role in (ROLE_TEACHER, ROLE_SUBJECT_TEACHER):
        from app.models.class_ import ClassTeacher

        legacy_ids = [row.id for row in db.query(Class).filter(Class.teacher_id == user.id)]
        relation_ids = [row.class_id for row in db.query(ClassTeacher).filter(ClassTeacher.teacher_id == user.id)]
        all_ids = set(legacy_ids + relation_ids)
        if not all_ids:
            return []
        return _classes_out(db, db.query(Class).filter(Class.id.in_(all_ids)).order_by(Class.id.desc()).offset(offset).limit(limit).all())
    # 学生：返回自己所在班级
    return _classes_out(
        db,
        db.query(Class)
        .join(ClassStudent, ClassStudent.class_id == Class.id)
        .filter(ClassStudent.student_id == user.id)
        .order_by(Class.id.desc())
        .offset(offset)
        .limit(limit)
        .all(),
    )


@router.get("/{class_id}", response_model=ClassOut)
def get_class(
    class_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cls = _check_class_owner(db, class_id, user)
    return _classes_out(db, [cls])[0]


@router.put("/{class_id}", response_model=ClassOut)
def update_class(
    class_id: int,
    body: ClassUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(_class_manager),
):
    cls = _check_class_owner(db, class_id, user)
    changes = body.model_dump(exclude_unset=True)
    if body.school_year is not None and body.school_year != cls.school_year and body.school_year_ends_on is None:
        # 切换学年时，未显式传结束日期则跟随新学年重算默认结束日。
        try:
            end_year = int(body.school_year.split("-", 1)[1])
            changes["school_year_ends_on"] = date(end_year, 7, 31)
        except (TypeError, ValueError, IndexError):
            pass
    education_stage = changes.get("education_stage", cls.education_stage)
    grade = changes.get("grade", cls.grade)
    class_type = changes.get("class_type", cls.class_type)
    short_term_type = changes.get("short_term_type", cls.short_term_type)
    # 编辑时基于“现有值 + 本次改动”整体校验，不能只校验单个字段。
    try:
        validate_class_category(education_stage, grade, class_type, short_term_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if body.name is not None:
        cls.name = body.name
    if body.education_stage is not None:
        cls.education_stage = body.education_stage
    if body.grade is not None:
        cls.grade = body.grade
    if body.class_type is not None:
        cls.class_type = body.class_type
    if "short_term_type" in changes:
        cls.short_term_type = body.short_term_type
    if body.school_year is not None:
        cls.school_year = body.school_year
    if body.school_year_starts_on is not None:
        cls.school_year_starts_on = body.school_year_starts_on
    if "school_year_ends_on" in changes:
        cls.school_year_ends_on = changes["school_year_ends_on"]
    if "teacher_id" in changes and changes["teacher_id"] is not None:
        new_teacher = db.get(User, changes["teacher_id"])
        if new_teacher is None or new_teacher.role != ROLE_TEACHER:
            raise HTTPException(status_code=400, detail="所选账号不是班主任")
        cls.teacher_id = new_teacher.id
    # 校验结束时间晚于开始时间
    if cls.school_year_ends_on <= cls.school_year_starts_on:
        raise HTTPException(status_code=422, detail="结束时间必须晚于开始时间")
    db.commit()
    db.refresh(cls)
    return _classes_out(db, [cls])[0]


@router.delete("/{class_id}")
def delete_class(
    class_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(_class_manager),
):
    """仅删除没有学生档案的班级，避免级联丢失档案记录。"""
    from app.models.student_case import StudentCase

    cls = _check_class_owner(db, class_id, user)
    blockers = []
    if db.query(StudentCase.id).filter_by(class_id=class_id).first():
        blockers.append("学生档案")
    if blockers:
        raise HTTPException(
            status_code=409,
            detail=f"该班级已关联{'、'.join(blockers)}，为防止数据丢失不能删除",
        )
    db.delete(cls)
    db.commit()
    return {"ok": True}


@router.post("/{class_id}/students", response_model=list[ClassStudentOut])
def add_students(
    class_id: int,
    body: StudentAdd,
    db: Session = Depends(get_db),
    user: User = Depends(_student_manager),
):
    """向班级批量添加学生（跳过非法/重复的 id）。"""
    _check_class_owner(db, class_id, user)
    added = []
    for sid in body.student_ids:
        stu = db.get(User, sid)
        if stu is None or stu.role != ROLE_STUDENT:
            continue
        exists = (
            db.query(ClassStudent)
            .filter(
                ClassStudent.class_id == class_id,
                ClassStudent.student_id == sid,
            )
            .first()
        )
        if exists:
            continue
        db.add(ClassStudent(class_id=class_id, student_id=sid))
        added.append(stu)
    db.commit()
    return added


def _ensure_user_profile_columns(db: Session) -> None:
    """历史兼容占位：users 档案扩展列已由迁移 w3x4y5z6a7b8/q7r8s9t0u1v2 保障。

    上线前已移除请求路径 DDL，避免并发建号锁表。保留空函数仅防旧导入报错。
    """


def _generate_student_username(db: Session, cls: Class, enrollment_month: int, seat_number: int) -> str:
    """学号规则：Y/U(初中Y 高中U)+年级(初一/高一=1,初二/高二=2,初三/高三=3)+年份后两位+入学月份(2位)+班号(2位)+位号(2位)。

    eg: Y326090101 = 初中(Y)+初三(3)+26届+09月+01班+01号。
    """
    import re
    from datetime import date as _date

    prefix = "U" if cls.education_stage == "高中" else "Y"
    grade_digit_map = {
        "初一": "1", "初二": "2", "初三": "3",
        "高一": "1", "高二": "2", "高三": "3",
        "复读": "4",
    }
    grade_digit = grade_digit_map.get((cls.grade or "").strip())
    if grade_digit is None:
        raise HTTPException(status_code=422, detail="当前班级年级无法生成学号")
    class_match = re.search(r"(\d+)", cls.name or "")
    class_number = int(class_match.group(1)) if class_match else cls.id or 1
    if class_number > 99:
        raise HTTPException(status_code=422, detail="班级编号不能超过99")
    # 年份后两位：优先从 school_year 起始年取（如 2026-2027 -> 26），异常时用当年
    year_two = ""
    try:
        year_full = str(cls.school_year or "").split("-", 1)[0].strip()
        if len(year_full) >= 2 and year_full.isdigit():
            year_two = year_full[-2:]
    except Exception:
        year_two = ""
    if not year_two or not year_two.isdigit():
        year_two = str(_date.today().year)[-2:]
    base = f"{prefix}{grade_digit}{year_two}{enrollment_month:02d}{class_number:02d}{seat_number:02d}"
    if db.query(User).filter(User.username == base).first() is None:
        return base
    raise HTTPException(status_code=409, detail=f"学号 {base} 已存在，请更换位号或入学月份")


@router.post("/{class_id}/students/create", response_model=ClassStudentOut)
def create_and_add_student(
    class_id: int,
    body: StudentCreateAndEnroll,
    db: Session = Depends(get_db),
    user: User = Depends(_student_manager),
):
    """在班级内直接新建学生账号并加入班级（仅录入档案信息，账号自动生成）。"""
    cls = _check_class_owner(db, class_id, user)
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="姓名不能为空")
    # 先校验咨询老师（选填）：避免建一半报错时残留未提交事务占用连接
    consultant = None
    if body.consultant_id is not None:
        consultant = db.get(User, body.consultant_id)
        if consultant is None or consultant.role not in (ROLE_TEACHER, ROLE_CONSULTANT):
            raise HTTPException(status_code=400, detail="所选咨询老师不存在")
    username = _generate_student_username(db, cls, body.enrollment_month, body.seat_number)
    # 默认初始密码 123456，班主任无需关心账号
    stu = User(
        username=username,
        password_hash=hash_password("123456"),
        name=name,
        role=ROLE_STUDENT,
        gender=(body.gender or "").strip(),
        ethnicity=(body.ethnicity or "").strip(),
        source_school=(body.source_school or "").strip(),
        grade=(body.grade or cls.grade or "").strip(),
        channel=(body.channel or "").strip(),
    )
    db.add(stu)
    db.flush()
    db.add(ClassStudent(class_id=class_id, student_id=stu.id))
    # 咨询老师选填：若传入则自动建立学生-咨询老师关联，方便后续在咨询侧展示
    if consultant is not None:
        db.add(StudentConsultant(consultant_id=consultant.id, student_id=stu.id))
    db.commit()
    db.refresh(stu)
    return stu


@router.get("/{class_id}/students", response_model=list[ClassStudentOut])
def list_students(
    class_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cls = _check_class_owner(db, class_id, user)
    return (
        db.query(User)
        .join(ClassStudent, ClassStudent.student_id == User.id)
        .filter(ClassStudent.class_id == cls.id)
        .order_by(User.id.asc())
        .all()
    )
