# 센터 사례 긴급도·분야 기본값 규칙. frontend/src/domain/centerCase.ts(rateUrgency·defaultCategory)와 1:1. 규칙 기반이며 LLM을 쓰지 않는다.

from app.schemas import CaseStatus, CoveragePath, RequestType, Urgency
from app.vocab import CaseCategory, YesNoUnknown


def rate_urgency(work_related: YesNoUnknown | None, insurance: YesNoUnknown | None) -> tuple[Urgency, list[str]]:
    score = 0
    reasons: list[str] = []
    if work_related == "yes":
        score += 2
        reasons.append("업무 중 발생")
    if insurance == "no":
        score += 1
        reasons.append("건강보험증 없음")
    urgency: Urgency = "high" if score >= 3 else "medium" if score >= 1 else "low"
    return urgency, reasons


def default_category(coverage_path: CoveragePath | None, request_types: list[RequestType]) -> CaseCategory:
    """접수 때 분야 기본값. 제도 경로와 요청 종류만 본다(증상 내용으로 가르지 않는다)."""
    if coverage_path == "ulsanSupport":
        return "cost"
    if coverage_path == "nhis" or request_types == ["policy"]:
        return "insurance"
    return "medical"


URGENCY_KO: dict[Urgency, str] = {"high": "높음", "medium": "보통", "low": "낮음"}
STATUS_KO: dict[CaseStatus, str] = {"new": "신규", "progress": "진행", "done": "완료"}
