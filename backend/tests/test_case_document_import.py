"""历史材料试导入：幂等、来源版本保留、待转换与教师确认边界。"""

from pathlib import Path

from app.models.student_case import (
    CaseDiagnosis,
    CaseImportDocument,
    StudentCase,
    SubjectPlan,
)
from app.models.user import USER_STATUS_DISABLED, User
from app.services.document_import_service import _split_comprehensive_field, run_pilot_import


def test_split_comprehensive_field_removes_next_number_and_expands_group():
    problem = "1. 语文：基础扎实；2. 数学：核心知识点漏洞多；3. 英语：词汇薄弱"
    causes = "1. 弱科（数、物、化、英）：基础积累不足；2. 语文/生物：迁移能力弱；3. 整体：时间分配不合理"

    problem_map = _split_comprehensive_field(problem)
    cause_map = _split_comprehensive_field(causes)

    assert problem_map["数学"] == "核心知识点漏洞多"
    assert cause_map["数学"] == "基础积累不足"
    assert cause_map["物理"] == "基础积累不足"
    assert cause_map["英语"] == "基础积累不足"


def test_pilot_import_is_idempotent_and_keeps_source_versions(
    client, auth, db, seed_users, tmp_path: Path, monkeypatch
):
    folders = ["高三甲同学", "高三乙同学", "高三丙同学", "高三丁同学", "高三戊同学"]
    for folder_name in folders:
        folder = tmp_path / folder_name
        folder.mkdir()
        student_name = folder_name.removeprefix("高三")
        (folder / f"一生一案要求（{student_name}）.docx").write_bytes(b"same-content")
    (tmp_path / folders[-1] / "物理旧稿.doc").write_bytes(b"legacy-doc")

    fields = {
        "problem_location": "基础知识不牢",
        "cause_analysis": "复盘不足",
        "struggle_goal": "稳定提升",
        "gaokao_requirement": "基础题正确率提升",
        "reinforcement": "每日限时训练",
    }
    monkeypatch.setattr(
        "app.services.document_import_service.extract_docx",
        lambda path: ("学生历史方案原文", fields, "数学"),
    )
    admin = db.get(User, seed_users["admin"])
    first = run_pilot_import(db, admin, tmp_path, folders, "test-pilot-batch")
    second = run_pilot_import(db, admin, tmp_path, folders, "test-pilot-batch")

    assert first.id == second.id
    assert second.summary == {
        "files": 6,
        "parsed": 5,
        "conversion_required": 1,
        "conflict": 0,
    }
    assert second.status == "needs_confirmation"
    assert db.query(CaseImportDocument).count() == 6
    assert db.query(CaseImportDocument.file_hash).distinct().count() == 2
    assert db.query(StudentCase).count() == 5
    assert db.query(SubjectPlan).count() == 5
    assert db.query(CaseDiagnosis).filter_by(is_confirmed=False).count() == 5
    imported_users = db.query(User).filter(User.username.like("g3_trial_%")).all()
    assert len(imported_users) == 5
    assert all(user.status == USER_STATUS_DISABLED for user in imported_users)

    batches = client.get("/api/student-cases/import-batches", headers=auth("admin"))
    assert batches.status_code == 200
    documents = client.get(
        f"/api/student-cases/import-batches/{first.id}/documents?status=conversion_required",
        headers=auth("admin"),
    )
    assert documents.status_code == 200
    assert [row["original_filename"] for row in documents.json()] == ["物理旧稿.doc"]
    assert client.get(
        "/api/student-cases/import-batches", headers=auth("teacher1")
    ).status_code == 403
