"""单人 DOCX 导出：严格复刻 docx/一生一案/导出模板 格式，不增内容/不改格式/不加颜色。"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from app.models.class_ import Class
from app.models.student_case import CaseCycle, CaseReview, CaseTask, StudentCase, SubjectPlan, TaskCheckin

# 模板路径（与用户指定一致）
TEMPLATE_COVER = Path(__file__).resolve().parents[3] / "docx" / "一生一案" / "导出模板" / "封面.docx"
TEMPLATE_BODY = Path(__file__).resolve().parents[3] / "docx" / "一生一案" / "导出模板" / "一生一案.docx"

# 若模板缺失则回退到通用模板（不应发生）
FALLBACK_TEMPLATE = Path(__file__).resolve().parents[3] / "docx" / "一生一案" / "模板" / "一生一案通用模板.docx"

SUBJECT_ORDER = ["语文", "数学", "英语", "物理", "化学", "生物", "政治", "历史", "地理", "德育"]


def _format_date(d) -> str:
    if not d:
        return ""
    try:
        return d.strftime("%Y/%m/%d")
    except Exception:
        return str(d).strip()


def _cadence_label(c: str) -> str:
    return {"daily": "日", "weekly": "周", "monthly": "月"}.get(c, c or "")


def _set_cell_text(cell, text: str) -> None:
    """仅替换文本，保留原有段落/Run 的字体、颜色、对齐等格式；\n 按段落拆分以保换行。"""
    # 清除多余段落，保留首段
    while len(cell.paragraphs) > 1:
        p = cell.paragraphs[1]
        p._element.getparent().remove(p._element)
    first_para = cell.paragraphs[0]
    # 记录首段的段落属性与首 run 的字符属性
    first_pPr = copy.deepcopy(first_para._p.get_or_add_pPr()) if first_para._p.get_or_add_pPr() is not None else None
    tmpl_rPr = copy.deepcopy(first_para.runs[0]._element.rPr) if first_para.runs and first_para.runs[0]._element.rPr is not None else None
    # 清空首段 runs
    for r in list(first_para.runs):
        r._element.getparent().remove(r._element)
    # 按换行拆段
    lines = (text or "").split("\n")
    # 首行写入首段
    run = first_para.add_run(lines[0] if lines else "")
    if tmpl_rPr is not None:
        run._element.get_or_add_rPr()
        run._element.rPr = copy.deepcopy(tmpl_rPr)
    # 其余行各起一段，复用首段的段落属性
    for line in lines[1:]:
        p = cell.add_paragraph()
        # 复用首段的段落属性
        if first_pPr is not None:
            p._p.get_or_add_pPr().append(copy.deepcopy(first_pPr))
            # 清理重复的 pPr 标记
            # 保留对齐等
        run = p.add_run(line)
        if tmpl_rPr is not None:
            run._element.get_or_add_rPr()
            run._element.rPr = copy.deepcopy(tmpl_rPr)


def _clone_body_elements(src_doc: Document, dst_doc: Document) -> None:
    """将 src_doc 的 body 所有子元素深拷贝到 dst_doc。"""
    for elem in list(src_doc.element.body):
        # 跳过 sectPr（节属性）由目标文档自带
        if elem.tag.endswith("sectPr"):
            continue
        dst_doc.element.body.append(copy.deepcopy(elem))


def _fill_cover_student_name(cover_elements: list, student_name: str, class_name: str) -> None:
    short_class = class_name.split("（")[0][:8] if class_name else class_name
    for elem in cover_elements:
        for t in elem.iter():
            if t.tag.endswith("}t") and t.text:
                if "赵书瑶" in t.text:
                    t.text = t.text.replace("赵书瑶", student_name)
                if "优学四班" in t.text:
                    t.text = t.text.replace("优学四班", short_class)


def build_case_export_bytes(
    case: StudentCase,
    student_name: str,
    class_name: str,
    cycle_name: str,
    subject_plans: list[SubjectPlan],
    tasks: list[CaseTask],
    checkins: list[TaskCheckin],
    reviews: list[CaseReview],
    cycle: CaseCycle | None = None,
) -> bytes:
    """生成单人 DOCX：严格复刻导出模板，不增内容、版式与颜色均沿用模板原样。"""
    # 载入模板
    cover_path = TEMPLATE_COVER if TEMPLATE_COVER.exists() else None
    body_path = TEMPLATE_BODY if TEMPLATE_BODY.exists() else (FALLBACK_TEMPLATE if FALLBACK_TEMPLATE.exists() else None)
    if body_path is None:
        raise FileNotFoundError("导出模板缺失：docx/一生一案/导出模板/一生一案.docx")

    body_tpl = Document(str(body_path))

    # 以封面为底，保留图片与 0 边距
    if TEMPLATE_COVER.exists():
        out = Document(str(TEMPLATE_COVER))
        for elem in out.element.body.iter():
            if elem.tag.endswith("}t") and elem.text:
                if "赵书瑶" in elem.text:
                    elem.text = elem.text.replace("赵书瑶", student_name)
                if "优学四班" in elem.text:
                    elem.text = elem.text.replace("优学四班", class_name.split("（")[0][:8])
        # 英文标题 distribute 会导致末字被裁，改居中
        for p in out.paragraphs:
            if "STUDENT" in p.text:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for elem in out.element.body.iter():
            if elem.tag.endswith("}p"):
                has_student = any(t.text and "STUDENT" in t.text for t in elem.iter() if t.tag.endswith("}t"))
                if has_student:
                    pPr = elem.find(qn("w:pPr"))
                    if pPr is not None:
                        jc = pPr.find(qn("w:jc"))
                        if jc is not None:
                            jc.set(qn("w:val"), "center")
        # 正文另起一节，沿用导出模板的纸张/边距，避免封面 0 边距污染表格
        if body_tpl.sections:
            from docx.shared import Cm
            body_sect = body_tpl.sections[0]._sectPr
            new_sectPr = OxmlElement("w:sectPr")
            for tag in ["w:pgSz", "w:pgMar", "w:cols", "w:docGrid"]:
                el = body_sect.find(qn(tag))
                if el is not None:
                    new_sectPr.append(copy.deepcopy(el))
            type_el = OxmlElement("w:type")
            type_el.set(qn("w:val"), "nextPage")
            new_sectPr.append(type_el)
            p = out.add_paragraph()
            p._p.append(new_sectPr)
    else:
        out = Document(str(body_path))
        body = out.element.body
        for child in list(body):
            if not child.tag.endswith("sectPr"):
                body.remove(child)

    plan_map = {p.subject: p for p in (subject_plans or [])}
    # 按固定顺序排序，模板本身为单科占位，这里为多科则循环生成多份
    ordered_subjects: list[str] = []
    if plan_map:
        # 已建立的学科按 SUBJECT_ORDER 排序，未建立的不导出空表（严格不加内容）
        for s in SUBJECT_ORDER:
            if s in plan_map:
                ordered_subjects.append(s)
        # 若存在非标准学科名，追加
        for s in plan_map:
            if s not in ordered_subjects:
                ordered_subjects.append(s)
    else:
        # 无学科方案时，仍导出空表一科（保持模板原样，不填）
        ordered_subjects = []

    # 若无任何学科，仍导出一遍空表（与模板一致，不额外提示）
    if not ordered_subjects:
        # 克隆 body 模板的全部元素（4段+1表）
        for elem in list(body_tpl.element.body):
            if elem.tag.endswith("sectPr"):
                continue
            out.element.body.append(copy.deepcopy(elem))
        bio = BytesIO()
        out.save(bio)
        return bio.getvalue()

    # 3) 为每科循环：克隆 body 模板的段落+表格，并填三列内容
    # 读取模板中表格的行列结构（11行4列，首行为表头）
    template_table = body_tpl.tables[0] if body_tpl.tables else None
    # 读取模板段落文本用于替换
    # P1 "科目 一生一案..." 中 "科目" 为占位
    # P2 "学生姓名：" 后接姓名

    for idx, subject in enumerate(ordered_subjects):
        plan = plan_map.get(subject)
        paras_before = len(out.paragraphs)
        tables_before = len(out.tables)

        # 克隆模板 body 的所有元素（段落+表格）
        # 为保持严格格式，直接深拷贝每个元素并替换文本
        for elem in list(body_tpl.element.body):
            if elem.tag.endswith("sectPr"):
                continue
            out.element.body.append(copy.deepcopy(elem))

        # 科目间一科一页，首科紧接封面（封面自带分页），后续科目用 pageBreakBefore
        if idx > 0:
            new_paras = out.paragraphs[paras_before : paras_before + 4]
            if new_paras:
                first_new = new_paras[0]
                pPr = first_new._p.get_or_add_pPr()
                pb = OxmlElement("w:pageBreakBefore")
                pb.set(qn("w:val"), "true")
                pPr.append(pb)

        # 定位刚 appended 的最后若干元素中的段落/表格进行填充
        # 由于刚 append 的是整段 body 的拷贝，我们通过 out 的末尾段落/表格数量来索引
        # 更可靠：直接在 out 的末尾找到最近添加的 4 个段落 + 1 个表格
        # 通过解析 out 的 paragraphs/tables 尾部

        # 找到末尾新增的段落
        # 约定：模板有 4 个段落（P0 学校名, P1 科目..., P2 学生姓名..., P3 空），随后 1 个表格
        # 我们按倒序查找
        # 填充 P1 的 "科目" -> subject
        # 此时 out.paragraphs 末尾 4 个即为本科技的段落
        recent_paras = out.paragraphs[-4:]
        if len(recent_paras) >= 3:
            # P1
            p1 = recent_paras[1] if len(recent_paras) >= 2 else None
            if p1 is not None and "科目" in p1.text:
                # 仅替换 "科目" 二字
                for r in p1.runs:
                    if "科目" in r.text:
                        r.text = r.text.replace("科目", subject)
                if "科目" not in p1.text:
                    # 若 runs 已拆分，兜底全量替换
                    p1.text = p1.text.replace("科目", subject)
            # P2 学生姓名：
            p2 = recent_paras[2] if len(recent_paras) >= 3 else None
            if p2 is not None and "学生姓名" in p2.text:
                # 保留前缀，追加姓名
                base = "学生姓名："
                p2.text = f"{base}{student_name}"
                # 同步设置中文字体不额外加色（沿用模板 run 格式）

        # 填充表格：取末尾最后一张表
        tbl = out.tables[-1]
        # 安全：确认 11 行
        if len(tbl.rows) < 11:
            continue
        # 任务/时间/督查 文本构造（不额外加颜色，仅文本）
        # 任务清单
        subject_tasks = [t for t in (tasks or []) if t.subject == subject]
        if subject_tasks:
            task_lines = []
            for t in subject_tasks:
                line = t.title or ""
                if t.description:
                    line = f"{line} {t.description[:200]}" if line else t.description[:200]
                # 周期与日期用简写
                line += f"（{_cadence_label(t.cadence)}·{_format_date(t.starts_on)}至{_format_date(t.due_on)}）"
                task_lines.append(line.strip())
            task_text = "\n".join(task_lines)[:1800]
        else:
            task_text = ""

        if subject_tasks:
            sched_lines = [f"{t.title}：{_format_date(t.starts_on)}至{_format_date(t.due_on)}" for t in subject_tasks]
            # 追加执行记录（若有）
            rel = [ch for ch in (checkins or []) if any(ts.id == ch.task_id and ts.subject == subject for ts in subject_tasks)]
            if rel:
                for ch in rel[:3]:
                    sched_lines.append(f"{_format_date(ch.checked_in_at)} {ch.completion_rate}%")
            sched_text = "\n".join(sched_lines)[:1200]
        else:
            sched_text = ""

        def latest_review(levels: set[str]) -> str:
            cand = [r for r in (reviews or []) if r.review_level in levels and (not r.subject or r.subject == subject or subject in (r.subject or ""))]
            if not cand:
                # 回退到不限学科的同层级
                cand = [r for r in (reviews or []) if r.review_level in levels]
            if not cand:
                return ""
            r = sorted(cand, key=lambda x: x.reviewed_at, reverse=True)[0]
            parts = []
            if r.problem:
                parts.append(r.problem[:300])
            if r.corrective_action:
                parts.append(r.corrective_action[:300])
            if r.correction_due_on:
                parts.append(f"截止：{_format_date(r.correction_due_on)}")
            if r.recheck_result:
                parts.append(f"复查：{r.recheck_result[:200]}")
            return "\n".join(parts)

        teacher_text = latest_review({"head_teacher", "subject"})
        principal_text = latest_review({"school", "principal"})

        # 映射：行号->文本（第2列为内容列，索引2）
        # R1 学科问题定位
        _set_cell_text(tbl.cell(1, 2), (plan.problem_location if plan else "") or "")
        _set_cell_text(tbl.cell(2, 2), (plan.cause_analysis if plan else "") or "")
        _set_cell_text(tbl.cell(3, 2), (plan.struggle_goal if plan else "") or "")
        _set_cell_text(tbl.cell(4, 2), (plan.gaokao_requirement if plan else "") or "")
        _set_cell_text(tbl.cell(5, 2), (plan.reinforcement if plan else "") or "")
        _set_cell_text(tbl.cell(6, 2), task_text or "")
        _set_cell_text(tbl.cell(7, 2), sched_text or "")
        _set_cell_text(tbl.cell(8, 2), "" )  # 学生自查保持空白（模板原样）
        _set_cell_text(tbl.cell(9, 2), teacher_text or "")
        _set_cell_text(tbl.cell(10, 2), principal_text or "")

    bio = BytesIO()
    out.save(bio)
    return bio.getvalue()
