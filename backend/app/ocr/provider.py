"""OCR 提供方抽象：mock 占位 + 通义千问 qwen-vl-ocr 实现。"""

from __future__ import annotations

import base64
import io
import logging
import time
from abc import ABC, abstractmethod

from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class OcrResult:
    """OCR 输出：提取的原始文本。"""

    def __init__(self, raw_text: str):
        self.raw_text = raw_text


class OcrProvider(ABC):
    @abstractmethod
    def extract(self, data: bytes, file_type: str) -> OcrResult:
        ...


class MockOcrProvider(OcrProvider):
    """开发期替身：返回占位文本，后续替换为真实第三方 OCR。"""

    def extract(self, data: bytes, file_type: str) -> OcrResult:
        return OcrResult(raw_text="[MockOCR] 题目图片内容待真实 OCR 识别")


class QwenOcrProvider(OcrProvider):
    """通义千问 qwen-vl-ocr（阿里云百炼，OpenAI 兼容接口）。

    - 图片：Base64 Data URL 直接送入
    - PDF：先按页渲染为 PNG 再逐页识别，按页合并输出
    """

    def __init__(self):
        self.client = OpenAI(
            base_url=settings.ocr_base_url,
            api_key=settings.ocr_api_key,
            timeout=settings.ocr_timeout_seconds,
            max_retries=settings.ocr_max_retries,
        )

    def extract(self, data: bytes, file_type: str) -> OcrResult:
        """入口：PDF 按页识别合并；图片单张识别。"""
        if file_type == "pdf":
            texts = []
            started = time.perf_counter()
            for page in self._pdf_pages(data):
                texts.append(self._extract_image(page))
            raw = "\n\n".join(texts)
            logger.info(
                "ocr_call_succeeded provider=qwen_ocr file_type=pdf pages=%s duration_ms=%s",
                len(texts),
                round((time.perf_counter() - started) * 1000),
            )
            return OcrResult(raw_text=raw)
        return OcrResult(raw_text=self._extract_image(data))

    def _extract_image(self, image_bytes: bytes) -> str:
        """单张图片转 Base64 Data URL 送入多模态模型提取文字。"""
        b64 = base64.b64encode(image_bytes).decode("ascii")
        started = time.perf_counter()
        try:
            resp = self.client.chat.completions.create(
                model=settings.ocr_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{b64}"
                                },
                            },
                            {
                                "type": "text",
                                "text": (
                                    "请提取图片中的全部文字内容，包括题目、学生手写作答等，"
                                    "严格按原顺序输出，不要添加任何解释或修改。"
                                ),
                            },
                        ],
                    }
                ],
            )
        except Exception:
            logger.exception(
                "ocr_call_failed provider=qwen_ocr model=%s", settings.ocr_model
            )
            raise
        raw = resp.choices[0].message.content or ""
        logger.info(
            "ocr_call_succeeded provider=qwen_ocr model=%s duration_ms=%s",
            resp.model or settings.ocr_model,
            round((time.perf_counter() - started) * 1000),
        )
        return raw

    @staticmethod
    def _pdf_pages(pdf_bytes: bytes) -> list[bytes]:
        """PDF 每页渲染为 2 倍缩放 PNG，供逐页 OCR。"""
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(pdf_bytes)
        pages: list[bytes] = []
        for i in range(len(pdf)):
            page = pdf[i]
            bitmap = page.render(scale=2.0)
            pil_image = bitmap.to_pil()
            buf = io.BytesIO()
            pil_image.save(buf, format="PNG")
            pages.append(buf.getvalue())
        pdf.close()
        return pages


_provider: OcrProvider | None = None


def get_ocr_provider() -> OcrProvider:
    """按配置懒加载 OCR 提供方（单例）。"""
    global _provider
    if _provider is None:
        if settings.ocr_provider == "mock":
            _provider = MockOcrProvider()
        elif settings.ocr_provider == "qwen":
            if not settings.ocr_api_key:
                raise RuntimeError(
                    "OCR_PROVIDER=qwen 需要配置 OCR_API_KEY（阿里云百炼 API Key）"
                )
            _provider = QwenOcrProvider()
        else:
            raise NotImplementedError(
                f"OCR provider '{settings.ocr_provider}' 不支持，可选：mock | qwen"
            )
    return _provider