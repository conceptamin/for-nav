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
    TranslationInfo,
    TriageResult,
    VisitHelperRequest,
    VisitHelperResponse,
)
from app.settings import settings
from app.templates.llm_slots import build_visit_helper
from app.templates.reports import build_center_summary, build_clinician_report
from app.templates.translate import SKIPPED, translate_note

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
async def visit_helper(req: VisitHelperRequest, llm: Annotated[LLMClient | None, Depends(llm_client)]) -> VisitHelperResponse:
    """S-09·S-10: 접수 창구 화면과 전화 스크립트. LLM이 있으면 자유 입력 요약으로 상황 줄 슬롯을 채운다."""
    return await build_visit_helper(
        req.intake, req.department, req.first_visit, req.lang, llm, timeout_s=settings.llm_timeout_s, attempts=settings.llm_attempts
    )


@router.post("/report/clinician")
async def report_clinician(req: ClinicianReportRequest, llm: Annotated[LLMClient | None, Depends(llm_client)]) -> ClinicianReport:
    """S-11: 의료진용 리포트. LLM이 있으면 자유 입력을 번역·역번역 검사해 note에 원문과 함께 넣는다."""
    # 근로자가 note를 뺐으면 자유 입력을 LLM에도 보내지 않는다.
    tr = (
        await translate_note(
            req.intake.free_text, req.intake.language, llm, timeout_s=settings.llm_timeout_s, attempts=settings.llm_attempts
        )
        if "note" in req.included
        else SKIPPED
    )
    report = build_clinician_report(req.intake, req.included, req.profile, req.meds, note_translation=tr.ko)
    report.llm_slots = []
    report.translation = TranslationInfo(status=tr.status)
    return report


@router.post("/report/center")
async def report_center(i: CenterSummaryInput, llm: Annotated[LLMClient | None, Depends(llm_client)]) -> CenterSummary:
    """S-12 미리보기: 센터 전송 요약. 실제 전송(POST /api/center/cases)과 같은 번역을 거친다."""
    tr = await translate_note(i.intake.free_text, i.intake.language, llm, timeout_s=settings.llm_timeout_s, attempts=settings.llm_attempts)
    summary = build_center_summary(i, note_translation=tr.ko)
    summary.translation = TranslationInfo(status=tr.status)
    return summary
