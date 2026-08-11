from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.config import settings


class OcrResult:
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


_provider: OcrProvider | None = None


def get_ocr_provider() -> OcrProvider:
    global _provider
    if _provider is None:
        if settings.ocr_provider == "mock":
            _provider = MockOcrProvider()
        else:
            raise NotImplementedError(
                f"OCR provider '{settings.ocr_provider}' 尚未接入，请配置 OCR_PROVIDER=mock"
            )
    return _provider
