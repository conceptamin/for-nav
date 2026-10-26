# 센터 접수함 API. 사례는 서버 메모리(store)에 두어 다른 기기에서도 "근로자 전송 → 센터 접수함 도착"을 시연한다.

from collections.abc import Callable
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Response, status

from app import clock
from app.data.mock import StatRecord
from app.rules.coverage import is_after_hours, next_open_day
from app.rules.urgency import rate_urgency
from app.schemas import CaseStatus, CenterCase, CenterStats, NewCaseRequest, NewCaseResponse, StatCell, StatusPatch
from app.store import store
from app.templates.reports import build_center_summary
from app.vocab import INDUSTRIES, District

router = APIRouter(prefix="/center")


@router.post("/cases", status_code=status.HTTP_201_CREATED)
def create_case(req: NewCaseRequest) -> NewCaseResponse:
    """S-12 전송. 요약·긴급도·운영 시간 외 여부·id·접수 시각은 서버가 같은 입력으로 다시 계산한다."""
    now = clock.now()
    summary = build_center_summary(req)
    urgency, reasons = rate_urgency(req.emergency_flag, req.intake.work_related, req.insurance)
    contact = (req.contact or "").strip() or None

    def make(case_id: str) -> CenterCase:
        return CenterCase(
            id=case_id,
            created_at=clock.iso_utc(now),
            language=req.intake.language,
            request_type=req.request_type,
            urgency=urgency,
            urgency_reasons=reasons,
            district=req.intake.district,
            industry=req.intake.industry,
            status="new",
            summary_ko=summary.ko,
            original_native=summary.native,
            consented_items=req.consented_items,
            coverage_path=req.coverage.path if req.coverage else None,
            contact_method=req.contact_method,
            contact=contact,
            after_hours=is_after_hours(now),
            emergency_flag=req.emergency_flag,
            work_related=req.intake.work_related,
            insurance=req.insurance,
            live=True,
        )

    c = store.add_live(now, make)
    return NewCaseResponse(case=c, next_open_date=next_open_day(now).isoformat())


@router.get("/cases")
def list_cases(status: CaseStatus | None = None, since: datetime | None = None) -> list[CenterCase]:
    """C-01: 최신순 목록. `since`를 주면 그 시각 이후에 접수된 사례만 돌려준다."""
    cases = store.all()
    if status:
        cases = [c for c in cases if c.status == status]
    if since:
        after = since if since.tzinfo else since.replace(tzinfo=clock.SEOUL)
        cases = [c for c in cases if clock.parse_iso(c.created_at) > after]
    return cases


def _not_found(case_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"사례 {case_id}를 찾을 수 없다")


@router.get("/cases/{case_id}")
def get_case(case_id: str) -> CenterCase:
    """C-02: 사례 상세."""
    c = store.get(case_id)
    if c is None:
        raise _not_found(case_id)
    return c


@router.patch("/cases/{case_id}")
def patch_case(case_id: str, body: StatusPatch) -> CenterCase:
    """C-02: 상태 변경."""
    c = store.set_status(case_id, body.status)
    if c is None:
        raise _not_found(case_id)
    return c


@router.post("/reset", status_code=status.HTTP_204_NO_CONTENT)
def reset() -> Response:
    """C-01 데모 초기화: live 사례와 상태 변경을 지운다."""
    store.reset()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# C-03 통계: 익명 집계만 돌려주고 5건 미만 칸은 서버에서 가린다(개인 단위 기록을 내보내지 않는다).
# ---------------------------------------------------------------------------
MIN_CELL = 5


def _mask(n: int) -> int | None:
    return n if n >= MIN_CELL else None


def _count_by[K](recs: list[StatRecord], keys: list[K], get: Callable[[StatRecord], K]) -> list[StatCell]:
    return [StatCell(key=str(k), n=_mask(sum(1 for r in recs if get(r) == k))) for k in keys]


STATS_DAYS = (30, 90, 180)


@router.get("/stats")
def stats(days: int = 90, district: District | None = None) -> CenterStats:
    """C-03: 기간(30·90·180일)·구군별 익명 집계."""
    if days not in STATS_DAYS:
        raise HTTPException(status_code=422, detail=f"days는 {STATS_DAYS} 중 하나여야 한다")
    since = clock.now() - timedelta(days=days)
    recs = [r for r in store.stat_records if r.date >= since and (district is None or r.district == district)]
    total = len(recs)
    after = sum(1 for r in recs if r.after_hours)
    shown = total >= MIN_CELL

    def rate(n: int) -> float | None:
        return n / total if shown else None

    return CenterStats(
        total=total if shown else None,
        after_hours_rate=rate(after),
        work_related_rate=rate(sum(1 for r in recs if r.work_related == "yes")),
        no_insurance_rate=rate(sum(1 for r in recs if r.insurance != "yes")),
        by_industry=_count_by(recs, list(INDUSTRIES), lambda r: r.industry),
        by_language=_count_by(recs, ["vi", "en"], lambda r: r.language),
        by_insurance=_count_by(recs, ["yes", "no", "unknown"], lambda r: r.insurance),
        by_after_hours=[StatCell(key="after", n=_mask(after)), StatCell(key="within", n=_mask(total - after))],
    )
