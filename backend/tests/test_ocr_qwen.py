"""qwen OCR provider 单元测试：验证图片/PDF 两条路径的请求构造与结果包装。"""

import base64
import json
import sys
import unittest.mock as mock

import pytest

from app.ocr.provider import MockOcrProvider, QwenOcrProvider


class FakeChoice:
    def __init__(self, content, model):
        self.message = mock.Mock(content=content)
        self.model = model


class FakeUsage:
    prompt_tokens = 10
    completion_tokens = 20
    total_tokens = 30


class FakeResp:
    choices = [FakeChoice("第1题：已知x=1，求y", "qwen-vl-ocr")]
    usage = FakeUsage()
    model = "qwen-vl-ocr"


def _fake_pdf_bytes():
    """构造一个最小合法 PDF（单页），用于渲染路径测试。"""
    return b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 100 100]>>endobj\nxref\n0 4\n0000000000 65535 f \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n0\n%%EOF"


@pytest.fixture()
def qwen(monkeypatch):
    p = QwenOcrProvider()
    p.client = mock.Mock()
    p.client.chat.completions.create.return_value = FakeResp()
    return p


def test_mock_provider():
    r = MockOcrProvider().extract(b"xx", "image")
    assert "MockOCR" in r.raw_text


def test_qwen_image_base64(qwen):
    img = b"\x89PNG\x0d\x0a\x1a\x0a" + b"\x00" * 16
    r = qwen.extract(img, "image")
    assert isinstance(r.raw_text, str)
    assert "第1题" in r.raw_text
    args = qwen.client.chat.completions.create.call_args
    content = args.kwargs["messages"][0]["content"]
    assert content[0]["type"] == "image_url"
    url = content[0]["image_url"]["url"]
    assert url.startswith("data:image/png;base64,")
    assert base64.b64decode(url.split(",", 1)[1]) == img
    assert content[1]["type"] == "text"


def test_qwen_pdf_pages_join(qwen, monkeypatch):
    monkeypatch.setattr(
        "app.ocr.provider.QwenOcrProvider._pdf_pages",
        lambda self, data: [b"PNG1", b"PNG2"],
    )
    r = qwen.extract(_fake_pdf_bytes(), "pdf")
    assert r.raw_text.count("第1题") == 2
    assert r.raw_text.count("\n\n") >= 1


def test_get_provider_no_key(monkeypatch):
    monkeypatch.setattr("app.ocr.provider.settings.ocr_provider", "qwen")
    monkeypatch.setattr("app.ocr.provider.settings.ocr_api_key", "")
    import importlib

    import app.ocr.provider as mod

    monkeypatch.setattr(mod, "_provider", None)
    with pytest.raises(RuntimeError, match="OCR_API_KEY"):
        mod.get_ocr_provider()