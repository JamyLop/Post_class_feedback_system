"""批改引擎基础结构与抽象基类。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.grading.schemas import GradeParams


@dataclass
class GradeResult:
    """一次批改的完整输出，供落库 submission_answers / grading_results 使用。"""

    score: float | None = None
    max_score: float = 0.0
    is_correct: bool | None = None
    confidence: float = 0.0
    error_type: str | None = None
    comment: str = ""
    error_points: list[dict] = field(default_factory=list)
    knowledge_points: list[dict] = field(default_factory=list)
    grading_type: str = ""
    model_name: str = ""
    raw_ai_result: dict | None = None
    prompt_version: str = ""


class BaseGrader(ABC):
    grading_type: str = "rule"

    @abstractmethod
    def grade(self, params: GradeParams) -> GradeResult:
        ...
