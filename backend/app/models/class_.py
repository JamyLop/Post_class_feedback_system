from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampMixin
from app.core.database import Base


class Class(TimestampMixin, Base):
    """班级表：归属某位教师。"""

    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    grade: Mapped[str] = mapped_column(String(32))
    education_stage: Mapped[str] = mapped_column(String(16), default="高中")
    class_type: Mapped[str] = mapped_column(String(16), default="全年班")
    short_term_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    school_year: Mapped[str] = mapped_column(String(16), default="未设置", index=True)
    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )


class ClassStudent(Base):
    """班级-学生多对多关联表（联合主键）。"""

    __tablename__ = "class_students"

    class_id: Mapped[int] = mapped_column(
        ForeignKey("classes.id", ondelete="CASCADE"), primary_key=True
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ClassTeacher(TimestampMixin, Base):
    """班级教师关系：明确班主任与学科教师，兼容 classes.teacher_id 旧数据。"""

    __tablename__ = "class_teachers"
    __table_args__ = (
        UniqueConstraint("class_id", "teacher_id", "subject", name="uq_class_teacher_subject"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(
        ForeignKey("classes.id", ondelete="CASCADE"), index=True
    )
    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(24), default="subject_teacher")
    # 班主任可不绑定学科；学科教师必须通过业务接口填写负责学科。
    subject: Mapped[str] = mapped_column(String(32), default="")


class StudentGuardian(TimestampMixin, Base):
    """家长与学生关系：家长只能读取已由班主任确认发布的学生总案。"""

    __tablename__ = "student_guardians"
    __table_args__ = (
        UniqueConstraint("parent_id", "student_id", name="uq_student_guardian"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    relationship: Mapped[str] = mapped_column(String(24), default="guardian")
