# 센터 접수함 API. 사례는 서버 메모리(store)에 두어 다른 기기에서도 "근로자 전송 → 센터 접수함 도착"을 시연한다.
# 사례마다 근로자·센터 상담 채팅(WebSocket, backlog 13)을 연다.

import secrets
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, WebSocket, status
from pydantic import ValidationError
from starlette.websockets import WebSocketDisconnect

from app import clock
from app.chat import ChatHub
from app.data.mock import StatRecord
from app.llm import LLMClient
from app.routers.worker import llm_client
from app.rules.coverage import is_after_hours, next_open_day
from app.rules.urgency import rate_urgency
from app.schemas import CaseStatus, CenterCase, CenterStats, ChatIn, ChatRole, NewCaseRequest, NewCaseResponse, StatCell, StatusPatch
from app.settings import settings
from app.store import store
from app.templates.reports import build_center_summary
from app.templates.translate import translate_note
from app.vocab import INDUSTRIES, District

router = APIRouter(prefix="/center")


@router.post("/cases", status_code=status.HTTP_201_CREATED)
async def create_case(req: NewCaseRequest, llm: Annotated[LLMClient | None, Depends(llm_client)]) -> NewCaseResponse:
    """S-12 전송. 요약·긴급도·운영 시간 외 여부·id·접수 시각은 서버가 같은 입력으로 다시 계산한다.

    요약의 자유 입력 번역은 미리보기(POST /api/report/center)와 같은 함수로 다시 만든다.
    """
    now = clock.now()
    tr = await translate_note(
        req.intake.free_text, req.intake.language, llm, timeout_s=settings.llm_timeout_s, attempts=settings.llm_attempts
    )
    summary = build_center_summary(req, note_translation=tr.ko)
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
    # 채팅 토큰은 이 응답으로 근로자에게만 간다. CenterCase에 넣지 않아 센터 목록·상세에는 나오지 않는다.
    token = secrets.token_urlsafe(24)
    store.set_chat_token(c.id, token)
    return NewCaseResponse(case=c, next_open_date=next_open_day(now).isoformat(), chat_token=token)


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
async def reset(request: Request) -> Response:
    """C-01 데모 초기화: live 사례, 상태 변경, 채팅을 지우고 열린 채팅 연결을 닫는다."""
    store.reset()
    hub: ChatHub = request.app.state.chat
    await hub.close_all()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# 상담 채팅(backlog 13): 사례 하나가 방 하나다. 검사에 실패하면 accept한 뒤 이유 코드로 닫는다
# (accept 전에 닫으면 클라이언트는 이유 없는 1006만 본다).
# ---------------------------------------------------------------------------
CLOSE_NOT_FOUND = 4404
CLOSE_FORBIDDEN = 4403
INVALID_FRAME = {"type": "error", "code": "invalid"}


def _chat_denied(case_id: str, role: str, token: str) -> int | None:
    if store.get(case_id) is None:
        return CLOSE_NOT_FOUND
    if role == "center":
        # 센터 화면에 로그인이 없어 데모에서는 역할만으로 붙는다(README "나중에 붙일 자리").
        return None
    expected = store.chat_token(case_id)
    if role == "worker" and expected and secrets.compare_digest(token.encode(), expected.encode()):
        return None
    return CLOSE_FORBIDDEN


@router.websocket("/cases/{case_id}/chat")
async def chat(ws: WebSocket, case_id: str, role: str = "", token: str = "") -> None:
    """근로자·센터 상담 채팅. 연결 직후 이전 메시지(history)를 한 번 보내고, 이후 메시지를 같은 방의 모든 연결에 보낸다."""
    await ws.accept()
    denied = _chat_denied(case_id, role, token)
    if denied:
        await ws.close(denied)
        return
    sender: ChatRole = "center" if role == "center" else "worker"
    hub: ChatHub = ws.app.state.chat
    # join과 이전 메시지 읽기 사이에 await가 없어야 그 사이 메시지를 놓치거나 두 번 받지 않는다.
    hub.join(case_id, ws)
    history = [m.model_dump(by_alias=True) for m in store.messages(case_id)]
    try:
        await ws.send_json({"type": "history", "messages": history})
        while True:
            message = await ws.receive()
            if message["type"] == "websocket.disconnect":
                break
            try:
                frame = ChatIn.model_validate_json(message.get("text") or "")
            except ValidationError:
                await ws.send_json(INVALID_FRAME)
                continue
            m = store.add_message(case_id, sender, frame.text, clock.now())
            await hub.broadcast(case_id, {"type": "message", "message": m.model_dump(by_alias=True)})
    except WebSocketDisconnect:
        pass
    finally:
        hub.leave(case_id, ws)


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
