"""开发种子数据：账号 + 知识点树 + 测试业务数据（日期为 8月19日）。

用法：python -m app.seed
"""
from datetime import date, datetime, timedelta, timezone

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.assignment import Assignment, AssignmentQuestion
from app.models.class_ import Class, ClassStudent
from app.models.feedback import (
    FEEDBACK_STATUS_PUBLISHED,
    FEEDBACK_TYPE_WEEKLY,
    FeedbackReport,
)
from app.models.grading import GRADING_STATUS_CONFIRMED, GradingResult
from app.models.knowledge import KnowledgePoint
from app.models.question import Question, QuestionKnowledgePoint
from app.models.submission import Submission, SubmissionAnswer
from app.models.user import ROLE_ADMIN, ROLE_STUDENT, ROLE_TEACHER, User

TZ_UTC8 = timezone(timedelta(hours=8))
NOW = datetime(2026, 8, 19, 10, 0, 0, tzinfo=TZ_UTC8)

ACCOUNTS = [
    {"username": "admin", "password": "admin123", "name": "系统管理员", "role": ROLE_ADMIN},
    {"username": "teacher1", "password": "teacher123", "name": "王老师", "role": ROLE_TEACHER},
    {"username": "student1", "password": "student123", "name": "张三", "role": ROLE_STUDENT},
    {"username": "student2", "password": "student123", "name": "李四", "role": ROLE_STUDENT},
    {"username": "student3", "password": "student123", "name": "王五", "role": ROLE_STUDENT},
]

KNOWLEDGE_TREE = [
    ("math_kp_root", "一元二次方程", None),
    ("math_kp_solve", "一元二次方程的解法", "math_kp_root"),
    ("math_kp_formula", "求根公式", "math_kp_solve"),
    ("math_kp_factor", "因式分解法", "math_kp_solve"),
    ("math_kp_quadratic", "二次函数", None),
    ("math_kp_graph", "二次函数图像", "math_kp_quadratic"),
    ("math_kp_vertex", "二次函数顶点", "math_kp_quadratic"),
    ("math_kp_axis", "对称轴", "math_kp_quadratic"),
    ("math_kp_inequality", "一元二次不等式", None),
]

QUESTIONS_DATA = [
    {"subject": "数学", "grade": "初中", "question_type": "single_choice",
     "content": "一元二次方程 x²-5x+6=0 的解是？", "standard_answer": "x=2 或 x=3",
     "score": 10, "difficulty": 0.3, "kp_codes": ["math_kp_factor"]},
    {"subject": "数学", "grade": "初中", "question_type": "fill",
     "content": "求根公式 x = (-b±√(b²-4ac))/2a 中，判别式 Δ=b²-4ac，当 Δ>0 时方程有____个实数根。",
     "standard_answer": "两", "score": 5, "difficulty": 0.4, "kp_codes": ["math_kp_formula"]},
    {"subject": "数学", "grade": "初中", "question_type": "judge",
     "content": "一元二次方程 2x²+3x+5=0 有两个不相等的实数根。",
     "standard_answer": "错", "score": 5, "difficulty": 0.5, "kp_codes": ["math_kp_formula"]},
    {"subject": "数学", "grade": "初中", "question_type": "short_answer",
     "content": "用配方法解方程 x²+6x-7=0，写出完整解题过程。",
     "standard_answer": "x=1 或 x=-7", "score": 15, "difficulty": 0.6, "kp_codes": ["math_kp_solve"]},
    {"subject": "数学", "grade": "初中", "question_type": "single_choice",
     "content": "二次函数 y=x²-4x+3 的顶点坐标是？", "standard_answer": "(2,-1)",
     "score": 10, "difficulty": 0.5, "kp_codes": ["math_kp_vertex"]},
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

        # ========== 2. 知识点树 ==========
        by_code: dict[str, int] = {}
        for code, name, parent_code in KNOWLEDGE_TREE:
            exists = db.query(KnowledgePoint).filter(KnowledgePoint.code == code).first()
            if exists is None:
                kp = KnowledgePoint(
                    subject="数学", grade="初中", chapter="方程与函数",
                    name=name, code=code,
                    parent_id=by_code.get(parent_code) if parent_code else None,
                )
                db.add(kp)
                db.flush()
                by_code[code] = kp.id
            else:
                by_code[code] = exists.id

        # ========== 3. 班级 ==========
        cls = db.query(Class).filter(Class.name == "八年级(1)班").first()
        if cls is None:
            cls = Class(name="八年级(1)班", grade="八年级", teacher_id=teacher1.id)
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

        # ========== 4. 题库 ==========
        q_ids: list[int] = []
        for qd in QUESTIONS_DATA:
            exists = db.query(Question).filter(Question.content == qd["content"]).first()
            if exists is None:
                q = Question(
                    subject=qd["subject"], grade=qd["grade"],
                    question_type=qd["question_type"], content=qd["content"],
                    standard_answer=qd["standard_answer"], score=qd["score"],
                    difficulty=qd["difficulty"],
                )
                db.add(q)
                db.flush()
                for kp_code in qd["kp_codes"]:
                    if kp_code in by_code:
                        db.add(QuestionKnowledgePoint(
                            question_id=q.id,
                            knowledge_point_id=by_code[kp_code],
                            weight=1.0,
                        ))
                q_ids.append(q.id)
            else:
                q_ids.append(exists.id)

        # ========== 5. 作业（8月19日发布，截止8月26日） ==========
        asgn = db.query(Assignment).filter(
            Assignment.title == "一元二次方程练习"
        ).first()
        if asgn is None:
            asgn = Assignment(
                class_id=cls.id, teacher_id=teacher1.id,
                title="一元二次方程练习", subject="数学",
                description="完成以下5道一元二次方程相关题目",
                due_at=datetime(2026, 8, 26, 23, 59, 0, tzinfo=TZ_UTC8),
                status="published",
                created_at=NOW,
            )
            db.add(asgn)
            db.flush()
            for idx, qid in enumerate(q_ids):
                exists = db.query(AssignmentQuestion).filter(
                    AssignmentQuestion.assignment_id == asgn.id,
                    AssignmentQuestion.question_id == qid,
                ).first()
                if exists is None:
                    db.add(AssignmentQuestion(
                        assignment_id=asgn.id, question_id=qid,
                        question_order=idx + 1,
                    ))

        # ========== 6. 学生提交（8月19日） ==========
        student_answers = [
            ["x=2 或 x=3", "两", "错", "x=1 或 x=-7", "(2,-1)"],
            ["x=2 或 x=3", "两", "对", "x=-1 或 x=-7", "(2,-1)"],
            ["x=1 或 x=3", "一", "错", "x=1 或 x=7", "(2,1)"],
        ]
        for idx, stu in enumerate(students):
            sub = db.query(Submission).filter(
                Submission.assignment_id == asgn.id,
                Submission.student_id == stu.id,
            ).first()
            if sub is None:
                sub = Submission(
                    assignment_id=asgn.id, student_id=stu.id,
                    content_type="text", status="ai_graded",
                    submitted_at=NOW + timedelta(hours=idx + 1),
                )
                db.add(sub)
                db.flush()
                for j, qid in enumerate(q_ids):
                    ans = SubmissionAnswer(
                        submission_id=sub.id, question_id=qid,
                        student_answer=student_answers[idx][j],
                        ocr_text=student_answers[idx][j],
                        is_correct=(j != idx),
                        score=QUESTIONS_DATA[j]["score"] if j != idx else QUESTIONS_DATA[j]["score"] * 0.6,
                        max_score=QUESTIONS_DATA[j]["score"],
                    )
                    db.add(ans)
                    db.flush()
                    grading = GradingResult(
                        submission_answer_id=ans.id,
                        grading_type="ai", model_name="deepseek-v4-flash",
                        ai_score=ans.score,
                        ai_comment="回答正确" if j != idx else "部分正确",
                        confidence=0.92,
                        status=GRADING_STATUS_CONFIRMED,
                        created_at=NOW + timedelta(hours=idx + 1, minutes=5),
                        reviewed_at=NOW + timedelta(hours=idx + 2),
                    )
                    db.add(grading)

        # ========== 7. 周反馈报告（8月12日-8月19日） ==========
        for stu in students:
            exists = db.query(FeedbackReport).filter(
                FeedbackReport.student_id == stu.id,
                FeedbackReport.class_id == cls.id,
                FeedbackReport.report_type == FEEDBACK_TYPE_WEEKLY,
            ).first()
            if exists is None:
                report = FeedbackReport(
                    student_id=stu.id, class_id=cls.id,
                    report_type=FEEDBACK_TYPE_WEEKLY,
                    period_start=date(2026, 8, 12),
                    period_end=date(2026, 8, 19),
                    status=FEEDBACK_STATUS_PUBLISHED,
                    input_snapshot={},
                    ai_content=f"{stu.name}本周学习表现良好，建议加强练习。",
                    final_content=f"{stu.name}本周学习表现良好，建议加强练习。",
                    model_name="deepseek-v4-flash",
                    generated_at=NOW - timedelta(hours=1),
                    published_at=NOW,
                )
                db.add(report)

        db.commit()
        print("Seed 完成（含 8月19日 测试数据）。")
        print("账号：admin/admin123, teacher1/teacher123, student1..3/student123")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
