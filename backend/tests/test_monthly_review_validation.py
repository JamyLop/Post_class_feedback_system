"""月度评定三个写入模型共用的字数边界。"""
import pytest
from pydantic import ValidationError

from app.schemas.monthly_report import (
    MonthlyEvaluationSave, MonthlyReportCreateIn, MonthlyReportUpdateIn,
)


def _payload(model, summary="结" * 50, problems="问" * 50, plan="改进"):
    content = f"【总结】\n{summary}\n\n【问题】\n{problems}\n\n【计划】\n{plan}"
    if model is MonthlyEvaluationSave:
        return {"content": content}
    data = {"final_content": content}
    if model is MonthlyReportCreateIn:
        data.update(student_id=1, class_id=1, month_label="2026-10")
    return data


@pytest.mark.parametrize("model", [MonthlyEvaluationSave, MonthlyReportCreateIn, MonthlyReportUpdateIn])
def test_review_minimum_per_field(model):
    model(**_payload(model))
    model(**_payload(model, summary="𠮷" * 50, problems="a" * 51, plan="做"))
    for field, label in (("summary", "总结"), ("problems", "问题")):
        for text in ("字" * 49, "字" * 49 + " \n\t　", "𠮷" * 49):
            with pytest.raises(ValidationError, match=f"{label}至少填写50字"):
                model(**_payload(model, **{field: text}))
    with pytest.raises(ValidationError, match="请完整填写"):
        model(**_payload(model, plan=" \n"))


def test_legacy_content_remains_readable_without_output_validation():
    # 输入校验不参与历史记录解析，也保留旧客户端的自由文本兼容。
    assert MonthlyEvaluationSave(content="历史自由文本").content == "历史自由文本"
