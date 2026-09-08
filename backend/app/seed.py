"""开发种子数据：账号、班级和任课关系。

用法：python -m app.seed
"""
from datetime import datetime, timedelta, timezone

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.class_ import Class, ClassStudent, ClassTeacher
from app.models.user import ROLE_ADMIN, ROLE_CONSULTANT, ROLE_DEYU_DIRECTOR, ROLE_STUDENT, ROLE_SUBJECT_TEACHER, ROLE_TEACHER, User

TZ_UTC8 = timezone(timedelta(hours=8))
NOW = datetime(2026, 8, 19, 10, 0, 0, tzinfo=TZ_UTC8)

ACCOUNTS = [
    {"username": "admin", "password": "admin123", "name": "系统管理员", "role": ROLE_ADMIN},
    {"username": "deyu1", "password": "deyu123", "name": "德育主任", "role": ROLE_DEYU_DIRECTOR},
    {"username": "teacher1", "password": "teacher123", "name": "王老师", "role": ROLE_TEACHER},
    {"username": "subject1", "password": "subject123", "name": "李老师（数学）", "role": ROLE_SUBJECT_TEACHER},
    {"username": "consultant1", "password": "consultant123", "name": "咨询老师", "role": ROLE_CONSULTANT},
    {"username": "student1", "password": "student123", "name": "张三", "role": ROLE_STUDENT},
    {"username": "student2", "password": "student123", "name": "李四", "role": ROLE_STUDENT},
    {"username": "student3", "password": "student123", "name": "王五", "role": ROLE_STUDENT},
]

def seed() -> None:
    """幂等播种：缺哪个数据就补哪个，已有则跳过。"""
    db = SessionLocal()
    try:
        # ========== 1. 账号 ==========
        for acc in ACCOUNTS:
            exists = db.query(User).filter(User.username == acc["username"]).first()
            if exists is None:
                db.add(User(
                    username=acc["username"],
                    password_hash=hash_password(acc["password"]),
                    name=acc["name"],
                    role=acc["role"],
                ))
        db.flush()

        teacher1 = db.query(User).filter(User.username == "teacher1").first()
        students = [
            db.query(User).filter(User.username == f"student{i}").first()
            for i in range(1, 4)
        ]

        # ========== 2. 班级 ==========
        cls = (
            db.query(Class)
            .filter(Class.name.in_(["初二(1)班", "八年级(1)班"]))
            .first()
        )
        if cls is None:
            cls = Class(
                name="初二(1)班",
                grade="初二",
                education_stage="初中",
                class_type="全年班",
                teacher_id=teacher1.id,
            )
            db.add(cls)
            db.flush()
            for stu in students:
                exists = db.query(ClassStudent).filter(
                    ClassStudent.class_id == cls.id,
                    ClassStudent.student_id == stu.id,
                ).first()
                if exists is None:
                    db.add(ClassStudent(
                        class_id=cls.id,
                        student_id=stu.id,
                        joined_at=NOW - timedelta(days=30),
                    ))

        # ========== 3. 任课关系（幂等）：subject1 担任该班数学任课老师 ==========
        subject1 = db.query(User).filter(User.username == "subject1").first()
        if subject1 is not None:
            link_exists = db.query(ClassTeacher).filter_by(
                class_id=cls.id, teacher_id=subject1.id, subject="数学"
            ).first()
            if link_exists is None:
                db.add(ClassTeacher(
                    class_id=cls.id,
                    teacher_id=subject1.id,
                    role="subject_teacher",
                    subject="数学",
                ))
                db.flush()

        db.commit()
        print("Seed 完成（账号、班级与任课关系）。")
        print("账号：admin/admin123, deyu1/deyu123, teacher1/teacher123, subject1/subject123, student1..3/student123")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
