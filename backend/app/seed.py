"""开发种子数据：账号 + 初中数学知识点树。

用法：python -m app.seed
"""
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.knowledge import KnowledgePoint
from app.models.user import ROLE_ADMIN, ROLE_STUDENT, ROLE_TEACHER, User

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


def seed() -> None:
    """幂等播种：缺哪个账号/知识点就补哪个，已有则跳过。"""
    db = SessionLocal()
    try:
        for acc in ACCOUNTS:
            exists = db.query(User).filter(User.username == acc["username"]).first()
            if exists is None:
                db.add(
                    User(
                        username=acc["username"],
                        password_hash=hash_password(acc["password"]),
                        name=acc["name"],
                        role=acc["role"],
                    )
                )
        # 知识点树：按父编码建立层级关系
        by_code: dict[str, int] = {}
        for code, name, parent_code in KNOWLEDGE_TREE:
            exists = (
                db.query(KnowledgePoint).filter(KnowledgePoint.code == code).first()
            )
            if exists is None:
                kp = KnowledgePoint(
                    subject="数学",
                    grade="初中",
                    chapter="方程与函数",
                    name=name,
                    code=code,
                    parent_id=by_code.get(parent_code) if parent_code else None,
                )
                db.add(kp)
                db.flush()
                by_code[code] = kp.id
            else:
                by_code[code] = exists.id
        db.commit()
        print("Seed 完成。")
        print("账号：admin/admin123, teacher1/teacher123, student1..3/student123")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
