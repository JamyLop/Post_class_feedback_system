"""单人 DOCX 导出：严格复刻 docx/一生一案/导出模板 格式，不增内容/不改格式/不加颜色。"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.enum.text import WD_BREAK

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
    """仅替换文本，保留原有段落/Run 的字体、颜色、对齐等格式。"""
    # 保留首段格式，清空多余段落
    # 清除除首段外所有段落
    while len(cell.paragraphs) > 1:
        p = cell.paragraphs[1]
        p._element.getparent().remove(p._element)
    para = cell.paragraphs[0]
    # 保留对齐等 pPr，清空 runs
    # 记录首个 run 的格式以复用
    if para.runs:
        tmpl_run = para.runs[0]
        tmpl_rPr = copy.deepcopy(tmpl_run._element.rPr) if tmpl_run._element.rPr is not None else None
    else:
        tmpl_rPr = None
    # 清空 para 内容（保留 pPr）
    for r in list(para.runs):
        r._element.getparent().remove(r._element)
    # 写入新文本，按原行用换行拆段（模板内可能无换行，此处保持换行语义）
    # 若文本含换行，则在同一 cell 内用换行符 br 分隔，保持单段
    # 简化：直接单 run 写入，换行用 \n 会被 Word 显示为换行
    run = para.add_run(text or "")
    if tmpl_rPr is not None:
        # 恢复模板 run 的 rPr
        run._element.get_or_add_rPr()
        # 用模板 rPr 覆盖（保留字体/字号/颜色）
        run._element.rPr = copy.deepcopy(tmpl_rPr)
    # 若模板无 run，则沿用 document 默认（不额外加色）


def _clone_body_elements(src_doc: Document, dst_doc: Document) -> None:
    """将 src_doc 的 body 所有子元素深拷贝到 dst_doc。"""
    for elem in list(src_doc.element.body):
        # 跳过 sectPr（节属性）由目标文档自带
        if elem.tag.endswith("sectPr"):
            continue
        dst_doc.element.body.append(copy.deepcopy(elem))


def _fill_cover_student_name(cover_elements: list, student_name: str, class_name: str) -> None:
    # 封面的学生/班级信息目前以图像底图为主，文本框内为示例（赵书瑶/优学四班）
    # 若存在 w:t 包含示例名/班，则替换；否则不额外新增，保持严格不加内容
    for elem in cover_elements:
        for t in elem.iter():
            if t.tag.endswith("}t") and t.text:
                if "赵书瑶" in t.text:
                    t.text = t.text.replace("赵书瑶", student_name)
                if "优学四班" in t.text:
                    t.text = t.text.replace("优学四班", class_name)
                # 兼容可能的英文 school 名不替换


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

    # 输出文档：以 body 模板为基底，清空后重建
    out = Document(str(body_path))
    # 清空 body（保留 sectPr）
    body = out.element.body
    for child in list(body):
        if not child.tag.endswith("sectPr"):
            body.remove(child)

    # 1) 先写入封面（若存在），保持其图像与版式
    if cover_path and cover_path.exists():
        cover_doc = Document(str(cover_path))
        # 深拷贝封面所有元素（图像底图+示例文字）
        cover_elems = list(cover_doc.element.body)
        # 替换示例姓名/班级（若存在）
        _fill_cover_student_name(cover_elems, student_name, class_name)
        for elem in cover_elems:
            if elem.tag.endswith("sectPr"):
                continue
            out.element.body.append(copy.deepcopy(elem))
        # 封面后分页（若封面与正文需分页，模板本身已含分页符则不再加）
        # 显式分页：插入 w:br w:type="page"
        # 仅当封面存在且正文将追加时，加分页段
        if len(cover_elems) > 0:
            p = out.add_paragraph()
            run = p.add_run()
            run.add_break(WD_BREAK.PAGE)

    # 2) 准备学科数据映射
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

        # 在每科之间（除首科）插入分页符，保持一科一页的打印效果（与历史材料一致）
        if idx > 0:
            p = out.add_paragraph()
            run = p.add_run()
            run.add_break(WD_BREAK.PAGE)

        # 克隆模板 body 的所有元素（段落+表格）
        # 为保持严格格式，直接深拷贝每个元素并替换文本
        for elem in list(body_tpl.element.body):
            if elem.tag.endswith("sectPr"):
                continue
            cloned = copy.deepcopy(elem)
            out.element.body.append(cloned)

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
