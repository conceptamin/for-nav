# 근로자 화면용 API. 규칙·템플릿을 그대로 부르며 상태를 저장하지 않는다.

from fastapi import APIRouter

from app.rules.coverage import route_coverage
from app.rules.triage import extract_from_text, filled_by_extraction, merge_extraction, triage
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
from app.templates.reports import build_center_summary, build_clinician_report
from app.templates.visit import build_call_script, build_desk_sheet

router = APIRouter()


@router.post("/extract")
def extract(req: ExtractRequest) -> ExtractResponse:
    """S-05 3단계: 자유 입력에서 부위·증상 등을 뽑아 빈 항목만 채운다(LLM 자리)."""
    ex = extract_from_text(req.intake.free_text)
    merged = merge_extraction(req.intake, ex)
    return ExtractResponse(extraction=ex, intake=merged, filled=filled_by_extraction(req.intake, merged))


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
