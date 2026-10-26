# 보험·제도 경로(POST /api/route)와 센터 운영 시간. frontend/src/domain/coverage.ts와 1:1.
# 판정이 아니라 "먼저 상담할 곳" 안내다. 같은 입력이면 같은 결과가 나오는 결정적 규칙이며 LLM을 쓰지 않는다.

from datetime import date, datetime, timedelta

from app.clock import SEOUL
from app.schemas import CenterHours, CoverageInput, CoveragePath, CoverageResult, Institution

# 제도 정보 기준일. 실제 운영 시 담당자가 확인한 날짜로 바꾼다.
INFO_DATE = "2026-10-24"

# 대표번호는 공개된 기관 대표번호만 둔다. 센터·울산시 지원사업 연락처는 미확인(PRD Q1·Q6).
KCOMWEL = Institution(id="kcomwel", phone="1588-0075")
NHIS = Institution(id="nhis", phone="1577-1000")
CENTER = Institution(id="center", phone=None)
ULSAN = Institution(id="ulsan", phone=None)


def route_coverage(i: CoverageInput) -> CoverageResult:
    base = {"info_date": INFO_DATE, "also_industrial": i.work_related == "unknown"}
    if i.work_related == "yes":
        return CoverageResult(**base, path="industrial", institutions=[KCOMWEL, CENTER], docs=["arc", "accidentNote", "photos", "receipts"])
    if i.insurance == "yes":
        return CoverageResult(**base, path="nhis", institutions=[NHIS, CENTER], docs=["arc", "insuranceCard", "meds"])
    if i.insurance == "no" and i.ulsan90 == "yes":
        return CoverageResult(**base, path="ulsanSupport", institutions=[CENTER, ULSAN], docs=["arc", "receipts"])
    return CoverageResult(**base, path="center", institutions=[CENTER], docs=["arc"])


PATH_KO: dict[CoveragePath, str] = {
    "industrial": "산재 상담 먼저",
    "nhis": "건강보험 진료",
    "ulsanSupport": "울산 의료비 지원 상담",
    "center": "센터 상담",
}

# ---------------------------------------------------------------------------
# 센터 운영 시간(설정값). PRD Q1 미결: 확인 전까지 평일 09:00~18:00으로 가정한다.
# 요일 번호는 프론트(JS Date.getDay)와 같이 0=일요일 … 6=토요일.
# 프론트는 브라우저 로컬 시각을 쓰지만 서버는 항상 Asia/Seoul 기준으로 계산한다.
# ---------------------------------------------------------------------------
CENTER_HOURS = CenterHours(open_hour=9, close_hour=18, workdays=[1, 2, 3, 4, 5])


def _js_day(d: datetime) -> int:
    return d.isoweekday() % 7


def is_after_hours(at: datetime) -> bool:
    d = at.astimezone(SEOUL)
    return _js_day(d) not in CENTER_HOURS.workdays or d.hour < CENTER_HOURS.open_hour or d.hour >= CENTER_HOURS.close_hour


def next_open_day(at: datetime) -> date:
    """다음 운영일(오늘 운영 시작 전이면 오늘)"""
    d = at.astimezone(SEOUL)
    if _js_day(d) in CENTER_HOURS.workdays and d.hour < CENTER_HOURS.open_hour:
        return d.date()
    d += timedelta(days=1)
    while _js_day(d) not in CENTER_HOURS.workdays:
        d += timedelta(days=1)
    return d.date()
