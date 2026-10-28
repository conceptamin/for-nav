# 근로자 화면용 API. 규칙·템플릿을 그대로 부르며 상태를 저장하지 않는다.

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.llm import LLMClient
from app.rules.coverage import route_coverage
from app.rules.extract_llm import extract_with_llm
from app.rules.triage import filled_by_extraction, merge_extraction, triage
from app.schemas import (
    CenterSummary,
    CenterSummaryInput,
    ClinicianReport,
    ClinicianReportRequest,
    CoverageInput,
    CoverageResult,
    ExtractRequest,
    ExtractResponse,
    Intake,
    TriageResult,
    VisitHelperRequest,
    VisitHelperResponse,
)
from app.settings import settings
from app.templates.reports import build_center_summary, build_clinician_report
from app.templates.visit import build_call_script, build_desk_sheet

router = APIRouter()


def llm_client(request: Request) -> LLMClient | None:
    """서버 시작 시 만든 LLM 클라이언트. 키가 없거나 lifespan 밖(테스트)이면 None이다."""
    return getattr(request.app.state, "llm", None)


@router.post("/extract")
async def extract(req: ExtractRequest, llm: Annotated[LLMClient | None, Depends(llm_client)]) -> ExtractResponse:
    """S-05 3단계: 자유 입력에서 부위·증상 등을 뽑아 빈 항목만 채운다. LLM이 없거나 실패하면 키워드 사전."""
    ex, source = await extract_with_llm(req.intake.free_text, llm, timeout_s=settings.llm_timeout_s, attempts=settings.llm_attempts)
    merged = merge_extraction(req.intake, ex)
    return ExtractResponse(extraction=ex, intake=merged, filled=filled_by_extraction(req.intake, merged), source=source)


@router.post("/triage")
def triage_(intake: Intake) -> TriageResult:
    """S-05: 응급 판정과 진료과 추천."""
    return triage(intake)


@router.post("/route")
def route(i: CoverageInput) -> CoverageResult:
    """S-08: 보험·제도 경로 안내."""
    return route_coverage(i)


@router.post("/visit-helper")
def visit_helper(req: VisitHelperRequest) -> VisitHelperResponse:
    """S-09·S-10: 접수 창구 화면과 전화 스크립트."""
    return VisitHelperResponse(
        desk=build_desk_sheet(req.intake, req.department, req.first_visit, req.lang),
        call=build_call_script(req.intake, req.department, req.lang),
    )


@router.post("/report/clinician")
def report_clinician(req: ClinicianReportRequest) -> ClinicianReport:
    """S-11: 의료진용 리포트."""
    return build_clinician_report(req.intake, req.included, req.profile, req.meds)


@router.post("/report/center")
def report_center(i: CenterSummaryInput) -> CenterSummary:
    """S-12 미리보기: 센터 전송 요약."""
    return build_center_summary(i)
