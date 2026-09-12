"""历史一生一案材料导入。

只读取原文件并保存来源快照；DOC/WPS 明确进入待转换，不把解析失败当成功。
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from hashlib import sha256
from pathlib import Path
import re
import secrets
from typing import Any
from zipfile import BadZipFile, ZipFile
from xml.etree import ElementTree as ET

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.class_ import Class, ClassStudent
from app.models.student_case import (
    CaseCycle,
    CaseDiagnosis,
    CaseImportBatch,
    CaseImportDocument,
    CaseTask,
    StudentCase,
    SubjectPlan,
)
from app.models.user import ROLE_STUDENT, USER_STATUS_DISABLED, User
from app.services.student_case_service import audit

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
SUPPORTED_EXTENSIONS = {".docx", ".doc", ".wps"}
SUBJECTS = ("语文", "数学", "英语", "物理", "化学", "生物", "政治", "历史", "地理", "德育")
FIELD_MAP = {
    "学科问题定位": "problem_location",
    "问题定位": "problem_location",
    "原因剖析": "cause_analysis",
    "奋斗目标": "struggle_goal",
    "高考要求": "gaokao_requirement",
    "具体强化": "reinforcement",
    "任务清单": "task_list",
    "具体时间安排": "schedule",
    "学生自查": "student_self_check",
    "教师督察": "teacher_supervision",
    "教师督查": "teacher_supervision",
    "校长检查": "school_supervision",
    "校级督查": "school_supervision",
}


def _node_text(node: ET.Element) -> str:
    return "".join(part.text or "" for part in node.iter(f"{W}t")).strip()


def extract_docx(path: Path) -> tuple[str, dict[str, str], str]:
    """使用 OOXML 标准库提取文本和四列表格，无需依赖本机 Word。"""
    try:
        with ZipFile(path) as archive:
            root = ET.fromstring(archive.read("word/document.xml"))
    except (BadZipFile, KeyError, ET.ParseError) as exc:
        raise ValueError("DOCX 文件结构损坏或不是有效 OOXML") from exc

    paragraphs = [_node_text(p) for p in root.iter(f"{W}p")]
    raw_text = "\n".join(text for text in paragraphs if text)
    parsed: dict[str, str] = {}
    for table in root.iter(f"{W}tbl"):
        for row in table.findall(f"{W}tr"):
            cells = [_node_text(cell) for cell in row.findall(f"{W}tc")]
            if len(cells) < 3:
                continue
            label = re.sub(r"\s+", "", cells[1])
            for source_label, field in FIELD_MAP.items():
                if source_label in label and cells[2].strip():
                    parsed.setdefault(field, cells[2].strip())
                    break

    search_area = f"{path.name}\n{raw_text[:500]}"
    found_subjects = [
        (search_area.index(item), item) for item in SUBJECTS if item in search_area
    ]
    subject = min(found_subjects)[1] if found_subjects else ""
    return raw_text, parsed, subject


def file_digest(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_pilot_structure(
    db: Session,
    actor: User,
    owner_teacher: User,
    student_names: list[str],
) -> tuple[CaseCycle, Class, dict[str, StudentCase]]:
    """幂等创建试点结构；新学生账号默认停用，等待学校确认身份。"""
    cycle = db.query(CaseCycle).filter_by(
        school_year="2026-2027", grade="高三"
    ).first()
    if cycle is None:
        cycle = CaseCycle(
            name="2026-2027学年",
            grade="高三",
            school_year="2026-2027",
            starts_on=date(2026, 8, 1),
            ends_on=date(2027, 6, 30),
            is_active=True,
        )
        db.add(cycle)
        db.flush()
    elif cycle.name != "2026-2027学年":
        # 存量数据兼容：旧名称含“高三备考周期”，统一修正为“2026-2027学年”
        cycle.name = "2026-2027学年"
        db.flush()

    cls = db.query(Class).filter_by(name="高三试点班（待确认）", grade="高三").first()
    if cls is None:
        cls = Class(
            name="高三试点班（待确认）",
            grade="高三",
            education_stage="高中",
            class_type="全年班",
            teacher_id=owner_teacher.id,
        )
        db.add(cls)
        db.flush()

    cases: dict[str, StudentCase] = {}
    for index, name in enumerate(student_names, start=1):
        student = db.query(User).filter(User.name == name, User.role == ROLE_STUDENT).first()
        if student is None:
            username = f"g3_trial_{index:03d}"
            existing = db.query(User).filter(User.username == username).first()
            if existing is not None and existing.name != name:
                username = f"g3_trial_{secrets.token_hex(4)}"
            student = User(
                username=username,
                password_hash=hash_password(secrets.token_urlsafe(32)),
                name=name,
                role=ROLE_STUDENT,
                status=USER_STATUS_DISABLED,
            )
            db.add(student)
            db.flush()
        member = db.query(ClassStudent).filter_by(
            class_id=cls.id, student_id=student.id
        ).first()
        if member is None:
            db.add(ClassStudent(class_id=cls.id, student_id=student.id))
        case = db.query(StudentCase).filter_by(
            cycle_id=cycle.id, student_id=student.id
        ).first()
        if case is None:
            case = StudentCase(
                cycle_id=cycle.id,
                student_id=student.id,
                class_id=cls.id,
                owner_teacher_id=owner_teacher.id,
                current_summary="历史DOCX试导入，待教师确认",
                status="draft",
            )
            db.add(case)
            db.flush()
            audit(db, actor.id, "case.import_create", "student_case", case.id, case.id)
        cases[name] = case
    return cycle, cls, cases


def _preferred_document(folder: Path, student_name: str) -> Path | None:
    preferred = [
        folder / f"一生一案要求（{student_name}）.docx",
        folder / f"一生一案（{student_name}）.docx",
    ]
    for path in preferred:
        if path.exists():
            return path
    candidates = sorted(folder.glob("*.docx"))
    return candidates[0] if candidates else None


def _split_comprehensive_field(text: str) -> dict[str, str]:
    """处理综合文档中以 '语文：'、'数学/物理：' 形式合并的多学科字段。"""
    if not text:
        return {}
    abbreviation_map = {
        "语": "语文", "数": "数学", "英": "英语", "物": "物理", "化": "化学",
        "生": "生物", "政": "政治", "史": "历史", "地": "地理", "德": "德育",
    }

    def expand_group(match: re.Match[str]) -> str:
        subjects = [
            abbreviation_map[item]
            for item in re.split(r'[、,/／ ]+', match.group(1))
            if item in abbreviation_map
        ]
        return f"{'/'.join(subjects)}：" if subjects else match.group(0)

    # 兼容“弱科（数、物、化、英）：...”这类综合原因写法。
    text = re.sub(
        r'(?:弱科|薄弱学科)?[（(]([语数英物化生政史地德](?:[、,/／ ]+[语数英物化生政史地德])+)[）)]\s*[：:]',
        expand_group,
        text,
    )
    pattern = r'((?:语文|数学|英语|物理|化学|生物|政治|历史|地理|德育)(?:[\/、／ ]+(?:语文|数学|英语|物理|化学|生物|政治|历史|地理|德育))*)[：:]'
    matches = list(re.finditer(pattern, text))
    if not matches:
        return {}
    result: dict[str, str] = {}
    for idx, match in enumerate(matches):
        label = match.group(1)
        subjects = [s for s in re.split(r'[\/、／ ]+', label) if s]
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        # 保留原文标号与标点，不做压缩，仅做首尾空白清理
        content = text[start:end].strip()
        # 仅去除因切分产生的首尾分隔符，保留编号如 "1. "
        content = content.strip(' \n')
        # 去掉切分导致的开头分隔符，但保留编号
        content = content.lstrip('；;，、 ')
        content = content.rstrip('；;，、 ')
        # 下一学科常写作“；3. 英语：”，切片位置在“英语”前，需移除遗留的编号。
        content = re.sub(r'[；;，、 ]*\d+[.、]\s*$', '', content).rstrip('；;，、 ')
        # 原因剖析中的 “；整体：...” 为全局总结，不应并入单科
        if '整体' in content:
            content = re.split(r'[；;]\s*整体[：:]', content)[0].strip().rstrip('；;，、 ')
        for subj in subjects:
            if subj in SUBJECTS:
                result[subj] = content
    return result


def _split_parenthesis_field(text: str) -> dict[str, str]:
    """处理如 '语文（81分）...、政治（15分）...' 的括号写法（徐援伟等文档）。"""
    if not text:
        return {}
    matches = list(re.finditer(r'(语文|数学|英语|物理|化学|生物|政治|历史|地理|德育)[（\(][^）\)]*[）\)]', text))
    if not matches:
        return {}
    result: dict[str, str] = {}
    for idx, match in enumerate(matches):
        subj = match.group(1)
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        snippet = text[start:end].strip(' ；;，、\n')
        snippet = snippet.lstrip('、，,；; ')
        # 去掉重复累积：若已存在则保留更长的描述
        if subj not in result or len(snippet) > len(result[subj]):
            result[subj] = snippet
    return result


def _extract_struggle_per_subject(text: str) -> dict[str, str]:
    """从奋斗目标的多阶段 '短期：数学60+、英语65+ ...' 中提炼每科目标。"""
    if not text:
        return {}
    per_subject: dict[str, list[str]] = {}
    stages = [p.strip() for p in re.split(r'[；;]', text) if p.strip()]
    # 若没有分号分隔，按行或逗号兜底
    if len(stages) == 1 and '：' not in text:
        stages = [text]
    for stage in stages:
        m = re.match(r'^([^：:]{1,20})[：:]\s*(.+)$', stage)
        if m:
            label, content = m.group(1).strip(), m.group(2).strip()
        else:
            # 兼容 "高考总分冲刺 350分：语文95+、..." 这种长标签
            m2 = re.match(r'^(.+?)[：:]\s*(.+)$', stage)
            if m2:
                label, content = m2.group(1).strip(), m2.group(2).strip()
            else:
                label, content = '', stage
        parts = [p.strip() for p in re.split(r'[、，,]', content) if p.strip()]
        for part in parts:
            for subj in SUBJECTS:
                if part.startswith(subj):
                    score = part[len(subj):].strip()
                    # 仅保留包含数字的目标，避免抓到描述性文字
                    if re.search(r'\d', score):
                        per_subject.setdefault(subj, []).append(f"{label}：{subj}{score}" if label else f"{subj}{score}")
                    break
    return {k: '；'.join(v) for k, v in per_subject.items() if v}


def _choose_per_subject_map(text: str) -> dict[str, str]:
    """优先按冒号拆分，失败则按括号拆分。"""
    mapped = _split_comprehensive_field(text)
    if mapped:
        return mapped
    return _split_parenthesis_field(text)


def _is_comprehensive_fields(fields: dict[str, Any]) -> bool:
    """综合材料至少在问题或奋斗目标中明确覆盖两个学科。"""
    problem_map = _choose_per_subject_map(fields.get("problem_location", ""))
    struggle_map = _extract_struggle_per_subject(fields.get("struggle_goal", ""))
    return len(problem_map) >= 2 or len(struggle_map) >= 2


def _stage_formal_suggestion(
    db: Session,
    case: StudentCase,
    document: CaseImportDocument,
    teacher_id: int,
) -> None:
    fields = document.parsed_fields or {}
    if not all(fields.get(name) for name in (
        "problem_location", "cause_analysis", "struggle_goal",
        "gaokao_requirement", "reinforcement",
    )):
        return

    # 综合文档包含多学科，需拆分为多个 SubjectPlan，避免单一“英语”计划承载全部内容
    problem_map = _choose_per_subject_map(fields["problem_location"])
    gaokao_map = _choose_per_subject_map(fields["gaokao_requirement"])
    reinforcement_map = _choose_per_subject_map(fields["reinforcement"])
    cause_map = _choose_per_subject_map(fields["cause_analysis"])
    struggle_map = _extract_struggle_per_subject(fields["struggle_goal"])

    # 判断是否为综合文档（含 ≥2 个学科）
    is_comprehensive = _is_comprehensive_fields(fields)
    if is_comprehensive:
        subjects = set(problem_map) | set(gaokao_map) | set(reinforcement_map) | set(cause_map) | set(struggle_map)
        for subject in subjects:
            problem_location = problem_map.get(subject) or fields["problem_location"]
            # 若该学科未在冒号拆分中出现，则尝试从原文按学科名截取，避免遗漏
            if subject not in problem_map:
                # 兜底：若综合字段过长，截取包含该学科的一段
                for seg in re.split(r'[；;]', fields["problem_location"]):
                    if subject in seg:
                        problem_location = seg.strip()
                        break
            cause_analysis = cause_map.get(subject) or fields["cause_analysis"]
            if subject not in cause_map:
                for seg in re.split(r'[；;]', fields["cause_analysis"]):
                    if subject in seg:
                        cause_analysis = seg.strip()
                        break
            struggle_goal = struggle_map.get(subject) or ''
            # 若提炼失败，兜底从原文提取该学科分数提及，仍保留原文不压缩
            if not struggle_goal:
                scores = re.findall(subject + r'(\d+(?:\.\d+)?\+?)', fields["struggle_goal"])
                if scores:
                    struggle_goal = '、'.join(f"{subject}{s}" for s in scores)
                else:
                    # 保留完整原文，避免内容丢失
                    struggle_goal = fields["struggle_goal"]
            gaokao_requirement = gaokao_map.get(subject, '')
            if not gaokao_requirement:
                for seg in re.split(r'[；;]', fields["gaokao_requirement"]):
                    if subject in seg:
                        gaokao_requirement = seg.strip()
                        break
                if not gaokao_requirement:
                    gaokao_requirement = fields["gaokao_requirement"]
            reinforcement = reinforcement_map.get(subject, '')
            if not reinforcement:
                for seg in re.split(r'[；;]', fields["reinforcement"]):
                    if subject in seg:
                        reinforcement = seg.strip()
                        break
                if not reinforcement:
                    reinforcement = fields["reinforcement"]
            plan = db.query(SubjectPlan).filter_by(
                student_case_id=case.id, subject=subject
            ).first()
            if plan is None:
                plan = SubjectPlan(
                    student_case_id=case.id,
                    subject=subject,
                    teacher_id=teacher_id,
                    problem_location=problem_location,
                    cause_analysis=cause_analysis,
                    struggle_goal=struggle_goal,
                    gaokao_requirement=gaokao_requirement,
                    reinforcement=reinforcement,
                    status="draft",
                )
                db.add(plan)
            else:
                plan.problem_location = problem_location
                plan.cause_analysis = cause_analysis
                if struggle_goal:
                    plan.struggle_goal = struggle_goal
                if gaokao_requirement:
                    plan.gaokao_requirement = gaokao_requirement
                if reinforcement:
                    plan.reinforcement = reinforcement
            # 每学科一条诊断
            existing_diagnosis = db.query(CaseDiagnosis).filter_by(
                student_case_id=case.id,
                subject=subject,
                category="historical_docx",
                source="docx_import",
            ).first()
            if existing_diagnosis is None:
                db.add(CaseDiagnosis(
                    student_case_id=case.id,
                    subject=subject,
                    category="historical_docx",
                    content=f"{problem_location}\n{cause_analysis}",
                    source="docx_import",
                    is_confirmed=False,
                ))
        # 根据 task_list 生成可执行任务，避免“0项任务”空白
        task_text = fields.get("task_list", "")
        schedule_text = fields.get("schedule", "")
        if task_text:
            task_map = _choose_per_subject_map(task_text)
            # 若未按学科切分（如单段“每日任务：xxx”），则按学科名兜底
            if not task_map:
                task_map = {}
                for subj in subjects:
                    for seg in re.split(r'[；;]', task_text):
                        if subj in seg:
                            task_map[subj] = seg.strip()
                            break
                    if subj not in task_map:
                        # 保留完整任务清单，避免压缩丢失
                        task_map[subj] = task_text[:200]
            for subj in subjects:
                content = task_map.get(subj, "")
                if not content:
                    continue
                # 避免重复创建
                exists = db.query(CaseTask).filter_by(student_case_id=case.id, subject=subj).first()
                if exists:
                    continue
                # 清理“每日任务：”前缀，保留实际内容
                content = re.sub(r'^[^：:]*任务[：:]\s*', '', content).strip()
                # 判定节奏
                cadence = "daily"
                if "每周" in task_text or "每周" in content:
                    cadence = "weekly"
                elif "每月" in task_text or "每月" in content:
                    cadence = "monthly"
                # 标题取前20字，避免过长
                title = f"{subj}每日强化任务" if cadence == "daily" else f"{subj}专项任务"
                if len(content) > 20:
                    title = f"{subj}：{content[:20]}"
                db.add(CaseTask(
                    student_case_id=case.id,
                    subject=subj,
                    title=title[:160],
                    description=(content + (f"\n时间安排：{schedule_text}" if schedule_text else ""))[:2000],
                    cadence=cadence,
                    starts_on=date.today(),
                    due_on=date(2027, 6, 30),
                    status="pending",
                    created_by=teacher_id,
                ))
        if not case.overall_problem:
            case.overall_problem = fields["problem_location"]
        if not case.admission_target:
            case.admission_target = fields["struggle_goal"]
        return

    # 单学科文档：保持原有逻辑
    subject = document.detected_subject or "综合"
    plan = db.query(SubjectPlan).filter_by(
        student_case_id=case.id, subject=subject
    ).first()
    if plan is None:
        plan = SubjectPlan(
            student_case_id=case.id,
            subject=subject,
            teacher_id=teacher_id,
            problem_location=fields["problem_location"],
            cause_analysis=fields["cause_analysis"],
            struggle_goal=fields["struggle_goal"],
            gaokao_requirement=fields["gaokao_requirement"],
            reinforcement=fields["reinforcement"],
            status="draft",
        )
        db.add(plan)
    else:
        # 独立学科文档优先于综合摘要，必须完整覆盖同学科的摘要字段。
        plan.teacher_id = teacher_id
        plan.problem_location = fields["problem_location"]
        plan.cause_analysis = fields["cause_analysis"]
        plan.struggle_goal = fields["struggle_goal"]
        plan.gaokao_requirement = fields["gaokao_requirement"]
        plan.reinforcement = fields["reinforcement"]
    existing_diagnosis = db.query(CaseDiagnosis).filter_by(
        student_case_id=case.id,
        subject=subject,
        category="historical_docx",
        source="docx_import",
    ).first()
    if existing_diagnosis is None:
        db.add(CaseDiagnosis(
            student_case_id=case.id,
            subject=subject,
            category="historical_docx",
            content=f"{fields['problem_location']}\n{fields['cause_analysis']}",
            source="docx_import",
            is_confirmed=False,
        ))
    if not case.overall_problem:
        case.overall_problem = fields["problem_location"]
    if not case.admission_target:
        case.admission_target = fields["struggle_goal"]


def run_pilot_import(
    db: Session,
    actor: User,
    source_root: Path,
    folder_names: list[str],
    batch_key: str,
) -> CaseImportBatch:
    root = source_root.resolve()
    if not root.is_dir():
        raise HTTPException(status_code=404, detail="历史材料目录不存在")
    if len(folder_names) != 5:
        raise HTTPException(status_code=400, detail="试导入必须恰好选择5名高三学生")
    if any(not name.startswith("高三") for name in folder_names):
        raise HTTPException(status_code=400, detail="第一版只允许高三学生目录")

    student_names = [name.removeprefix("高三").strip() for name in folder_names]
    owner_teacher = db.query(User).filter(User.role == "teacher").order_by(User.id).first()
    if owner_teacher is None:
        raise HTTPException(status_code=409, detail="数据库中没有可作为负责人的教师账号")
    _, _, cases = ensure_pilot_structure(db, actor, owner_teacher, student_names)
    batch = db.query(CaseImportBatch).filter_by(batch_key=batch_key).first()
    if batch is None:
        batch = CaseImportBatch(
            batch_key=batch_key,
            scope_grade="高三",
            source_root=str(root),
            selected_students=student_names,
            status="processing",
            created_by=actor.id,
        )
        db.add(batch)
        db.flush()

    counts = {"parsed": 0, "conversion_required": 0, "conflict": 0, "files": 0}
    for folder_name, student_name in zip(folder_names, student_names):
        folder = (root / folder_name).resolve()
        if folder.parent != root or not folder.is_dir():
            counts["conflict"] += 1
            continue
        files = sorted(
            path for path in folder.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        )
        for version, path in enumerate(files, start=1):
            relative_path = str(path.relative_to(root))
            existing = db.query(CaseImportDocument).filter_by(
                batch_id=batch.id, original_path=relative_path
            ).first()
            if existing is not None:
                continue
            ext = path.suffix.lower()
            raw_text = ""
            parsed_fields: dict[str, Any] = {}
            subject = ""
            status = "conversion_required" if ext in {".doc", ".wps"} else "parsed"
            reason = "需先转换为DOCX后再解析" if status == "conversion_required" else ""
            if ext == ".docx":
                try:
                    raw_text, parsed_fields, subject = extract_docx(path)
                    if not raw_text:
                        status, reason = "conflict", "文档未提取到文本，需人工确认"
                except ValueError as exc:
                    status, reason = "conflict", str(exc)
            document = CaseImportDocument(
                batch_id=batch.id,
                student_case_id=cases[student_name].id,
                detected_student_name=student_name,
                detected_subject=subject,
                original_path=relative_path,
                original_filename=path.name,
                file_ext=ext,
                file_hash=file_digest(path),
                source_version=version,
                file_size=path.stat().st_size,
                raw_text=raw_text,
                parsed_fields=parsed_fields,
                status=status,
                conflict_reason=reason,
            )
            db.add(document)
            db.flush()
            counts["files"] += 1
            counts[status] += 1
        # 先写综合材料，再写独立学科材料；后者完整度更高，禁止被摘要反向覆盖。
        parsed_documents = db.query(CaseImportDocument).filter_by(
            batch_id=batch.id,
            student_case_id=cases[student_name].id,
            status="parsed",
        ).all()
        parsed_documents.sort(key=lambda row: (
            not _is_comprehensive_fields(row.parsed_fields or {}),
            sum(len(value or "") for value in (row.parsed_fields or {}).values()),
        ))
        for parsed_document in parsed_documents:
            _stage_formal_suggestion(
                db, cases[student_name], parsed_document, owner_teacher.id
            )

    stored_documents = db.query(CaseImportDocument).filter_by(batch_id=batch.id).all()
    counts = {
        "files": len(stored_documents),
        "parsed": sum(row.status == "parsed" for row in stored_documents),
        "conversion_required": sum(row.status == "conversion_required" for row in stored_documents),
        "conflict": sum(row.status == "conflict" for row in stored_documents),
    }
    batch.status = "needs_confirmation" if counts["conflict"] or counts["conversion_required"] else "completed"
    batch.summary = counts
    batch.finished_at = datetime.now(timezone.utc)
    audit(db, actor.id, "case_import.complete", "case_import_batch", batch.id, detail=counts)
    db.commit()
    db.refresh(batch)
    return batch
