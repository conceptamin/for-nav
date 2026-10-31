# 센터 접수함 API. 사례는 서버 메모리(store)에 두어 다른 기기에서도 "근로자 전송 → 센터 접수함 도착"을 시연한다.
# 사례마다 근로자·센터 상담 채팅(WebSocket, backlog 14)과 통화 시그널링·자막 번역(backlog 16)을 연다.
# CENTER_AUTH=email이면 센터 읽기·쓰기와 채팅·통화의 role=center는 직원 세션이 있어야 한다(backlog 17).
# 근로자 전송(POST /cases)은 직원 세션을 보지 않고, WORKER_AUTH=google일 때만 근로자 세션이 있어야 한다(backlog 21).
# 근로자 앱 푸시(backlog 28): 채팅 토큰으로 기기를 사례에 묶고, 센터 채팅 글·상태 변경 뒤 응답을 막지 않고 백그라운드로 보낸다.

import asyncio
import logging
import secrets
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Annotated
from urllib.parse import urlsplit

import anyio
from fastapi import APIRouter, Depends, HTTPException, Request, Response, WebSocket, status
from pydantic import TypeAdapter, ValidationError
from starlette.websockets import WebSocketDisconnect

from app import auth, clock
from app.chat import CallHub, ChatHub
from app.data.mock import StatRecord
from app.llm import LLMClient
from app.push import PushNotifier
from app.routers.worker import llm_client
from app.rules.coverage import is_after_hours, next_open_day
from app.rules.urgency import rate_urgency
from app.schemas import (
    CallCaptionIn,
    CallIn,
    Caption,
    CaseStatus,
    CenterCase,
    CenterStats,
    ChatIn,
    ChatReadIn,
    ChatRole,
    MyCasesRequest,
    MyCaseView,
    NewCaseRequest,
    NewCaseResponse,
    PushDeviceRemove,
    PushDeviceRequest,
    PushDeviceResponse,
    StatCell,
    StatusPatch,
)
from app.settings import settings
from app.store import message_number, store
from app.templates.reports import build_center_summary
from app.templates.translate import translate_line, translate_note
from app.vocab import INDUSTRIES, District, Lang

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/center")


def require_staff(request: Request) -> None:
    """센터 읽기·쓰기 경로에 거는 의존성. 근로자 전송(POST /cases)에는 걸지 않는다."""
    if settings.center_auth != "email":
        return
    if auth.session_email(store, request.cookies.get(auth.COOKIE), clock.now()) is None:
        raise HTTPException(status_code=401, detail="센터 로그인이 필요하다")


staff_only = [Depends(require_staff)]


def require_worker(request: Request) -> None:
    """근로자 전송(POST /cases)에 거는 의존성. 센터 요청은 회원만 보낸다(PRD). 판정·안내 경로에는 걸지 않는다."""
    if settings.worker_auth != "google":
        return
    if auth.worker_account(store, request.cookies.get(auth.WORKER_COOKIE), clock.now()) is None:
        raise HTTPException(status_code=401, detail="근로자 로그인이 필요하다")


@router.post("/cases", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_worker)])
async def create_case(req: NewCaseRequest, llm: Annotated[LLMClient | None, Depends(llm_client)]) -> NewCaseResponse:
    """S-12 전송. 요약·긴급도·운영 시간 외 여부·id·접수 시각은 서버가 같은 입력으로 다시 계산한다.

    요약의 자유 입력 번역은 미리보기(POST /api/report/center)와 같은 함수로 다시 만든다.
    """
    now = clock.now()
    tr = await translate_note(
        req.intake.free_text, req.intake.language, llm, timeout_s=settings.llm_timeout_s, attempts=settings.llm_attempts
    )
    summary = build_center_summary(req, note_translation=tr.ko)
    urgency, reasons = rate_urgency(req.intake.work_related, req.insurance)
    contact = (req.contact or "").strip() or None

    def make(case_id: str) -> CenterCase:
        return CenterCase(
            id=case_id,
            created_at=clock.iso_utc(now),
            language=req.intake.language,
            request_types=req.request_types,
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
            work_related=req.intake.work_related,
            insurance=req.insurance,
            live=True,
        )

    c = store.add_live(now, make)
    # 채팅 토큰은 이 응답으로 근로자에게만 간다. CenterCase에 넣지 않아 센터 목록·상세에는 나오지 않는다.
    token = secrets.token_urlsafe(24)
    store.set_chat_token(c.id, token)
    return NewCaseResponse(case=c, next_open_date=next_open_day(now).isoformat(), chat_token=token)


def _owned_case(case_id: str, token: str) -> CenterCase | None:
    """채팅 토큰이 맞는 사례. 토큰이 틀리거나 사례가 없으면 None이다(이유를 나누지 않는다)."""
    expected = store.chat_token(case_id)
    if not expected or not secrets.compare_digest(token.encode(), expected.encode()):
        return None
    return store.get(case_id)


@router.post("/my-cases", dependencies=[Depends(require_worker)])
def my_cases(req: MyCasesRequest) -> list[MyCaseView]:
    """S-13·센터 채팅 시트: 근로자가 채팅 토큰으로 자기 요청의 상태와 센터 메시지 수를 읽는다(backlog 27).

    토큰이 틀리거나 사례가 없으면 그 항목만 뺀다. 사례가 있는지 드러내지 않으려고 403·404를 내지 않는다.
    """
    out: list[MyCaseView] = []
    for ref in req.cases:
        c = _owned_case(ref.id, ref.token)
        if c is None:
            continue
        count, last = store.center_message_summary(ref.id)
        out.append(MyCaseView(id=c.id, status=c.status, center_messages=count, last_center_at=last))
    return out


@router.post("/push-devices", dependencies=[Depends(require_worker)])
def register_push_device(req: PushDeviceRequest) -> PushDeviceResponse:
    """근로자 앱이 FCM 기기 토큰을 채팅 토큰이 맞는 사례에 묶는다(backlog 28). PUSH=off여도 그대로 동작한다.

    틀린 토큰·없는 사례는 my-cases와 같이 오류 없이 빠진다. 같은 기기·사례를 다시 보내면 platform·notice·갱신 시각만 바뀐다.
    """
    now = clock.now()
    bound: list[str] = []
    for ref in req.cases:
        if ref.id in bound or _owned_case(ref.id, ref.token) is None:
            continue
        store.add_push_device(ref.id, req.device_token, req.platform, req.notice, now)
        bound.append(ref.id)
    return PushDeviceResponse(cases=bound)


@router.post("/push-devices/remove", status_code=status.HTTP_204_NO_CONTENT)
def remove_push_device(req: PushDeviceRemove) -> Response:
    """그 기기의 묶음을 모두 지운다. 없는 토큰도 204다.

    근로자 세션을 보지 않는다: 웹이 로그아웃 직후(세션이 이미 끝났을 때) 부르고, 기기 토큰 자체가 열쇠다.
    """
    store.remove_push_device(req.device_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _notify(app_state, case_id: str) -> None:
    """푸시 발송을 띄운다. 근로자가 그 사례 채팅을 보고 있으면 건너뛴다. 기다리지 않는다."""
    hub: ChatHub = app_state.chat
    push: PushNotifier = app_state.push
    push.notify(store, case_id, clock.now(), watching=hub.has_worker(case_id))


@router.get("/cases", dependencies=staff_only)
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


@router.get("/cases/{case_id}", dependencies=staff_only)
def get_case(case_id: str) -> CenterCase:
    """C-02: 사례 상세."""
    c = store.get(case_id)
    if c is None:
        raise _not_found(case_id)
    return c


@router.patch("/cases/{case_id}", dependencies=staff_only)
async def patch_case(case_id: str, body: StatusPatch, request: Request) -> CenterCase:
    """C-02: 상태 변경. 상태가 실제로 바뀌었을 때만 근로자 기기에 알린다(backlog 28)."""
    before = store.get(case_id)
    c = store.set_status(case_id, body.status)
    if before is None or c is None:
        raise _not_found(case_id)
    if c.status != before.status:
        _notify(request.app.state, case_id)
    return c


@router.post("/reset", status_code=status.HTTP_204_NO_CONTENT, dependencies=staff_only)
async def reset(request: Request) -> Response:
    """C-01 데모 초기화: live 사례, 상태 변경, 채팅, 통화 자막을 지우고 열린 채팅·통화 연결을 닫는다."""
    store.reset()
    hub: ChatHub = request.app.state.chat
    await hub.close_all()
    call_hub: CallHub = request.app.state.call
    await call_hub.close_all()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# 상담 채팅(backlog 14): 사례 하나가 방 하나다. 검사에 실패하면 accept한 뒤 이유 코드로 닫는다
# (accept 전에 닫으면 클라이언트는 이유 없는 1006만 본다).
# ---------------------------------------------------------------------------
CLOSE_NOT_FOUND = 4404
CLOSE_FORBIDDEN = 4403
# role=center인데 직원 세션이 없거나 끝났다(backlog 17)
CLOSE_UNAUTHORIZED = 4401
INVALID_FRAME = {"type": "error", "code": "invalid"}
_CHAT_IN: TypeAdapter[ChatIn] = TypeAdapter(ChatIn)


def _same_site(ws: WebSocket) -> bool:
    """다른 사이트의 페이지가 직원 쿠키를 실어 붙는 것을 막는다. Origin이 없으면 브라우저가 아니므로 쿠키 확인에 맡긴다."""
    origin = ws.headers.get("origin")
    if origin is None or origin in settings.cors_origins:
        return True
    return urlsplit(origin).netloc == ws.headers.get("host", "")


def _chat_denied(ws: WebSocket, case_id: str, role: str, token: str) -> int | None:
    if store.get(case_id) is None:
        return CLOSE_NOT_FOUND
    if role == "center":
        # CENTER_AUTH=off이면 센터 화면에 로그인이 없어 역할만으로 붙는다.
        if settings.center_auth != "email":
            return None
        if not _same_site(ws):
            return CLOSE_FORBIDDEN
        if auth.session_email(store, ws.cookies.get(auth.COOKIE), clock.now()) is None:
            return CLOSE_UNAUTHORIZED
        return None
    expected = store.chat_token(case_id)
    if role == "worker" and expected and secrets.compare_digest(token.encode(), expected.encode()):
        return None
    return CLOSE_FORBIDDEN


@router.websocket("/cases/{case_id}/chat")
async def chat(ws: WebSocket, case_id: str, role: str = "", token: str = "") -> None:
    """근로자·센터 상담 채팅. 연결 직후 이전 메시지와 역할별 읽은 자리(history)를 한 번 보내고,
    이후 메시지와 읽음(backlog 28)을 같은 방의 모든 연결에 보낸다."""
    await ws.accept()
    denied = _chat_denied(ws, case_id, role, token)
    if denied:
        await ws.close(denied)
        return
    sender: ChatRole = "center" if role == "center" else "worker"
    hub: ChatHub = ws.app.state.chat
    # join과 이전 메시지 읽기 사이에 await가 없어야 그 사이 메시지를 놓치거나 두 번 받지 않는다.
    hub.join(case_id, ws, sender)
    history = [m.model_dump(by_alias=True) for m in store.messages(case_id)]
    try:
        await ws.send_json({"type": "history", "messages": history, "read": store.read_marks(case_id)})
        while True:
            message = await ws.receive()
            if message["type"] == "websocket.disconnect":
                break
            try:
                frame = _CHAT_IN.validate_json(message.get("text") or "")
            except ValidationError:
                await ws.send_json(INVALID_FRAME)
                continue
            if isinstance(frame, ChatReadIn):
                # 아직 없는 메시지까지 읽었다고 할 수 없다. 앞으로 옮겨졌을 때만 알린다
                n = message_number(frame.up_to)
                if n is None or n > len(store.messages(case_id)):
                    await ws.send_json(INVALID_FRAME)
                elif store.mark_read(case_id, sender, n):
                    await hub.broadcast(case_id, {"type": "read", "role": sender, "upTo": frame.up_to})
                continue
            m = store.add_message(case_id, sender, frame.text, clock.now())
            await hub.broadcast(case_id, {"type": "message", "message": m.model_dump(by_alias=True)})
            if sender == "center":
                _notify(ws.app.state, case_id)
    except WebSocketDisconnect:
        pass
    finally:
        hub.leave(case_id, ws)


# ---------------------------------------------------------------------------
# 통화(backlog 16): 음성은 브라우저끼리 WebRTC로 오가고, 서버는 시그널링을 상대에게 중계하고 받아쓴 문장을 번역한다.
# 자막은 사례별로 저장하고(backlog 18) 연결 직후 history로 다시 준다. 권한·닫힘 코드는 채팅과 같다. 로그에는 SDP·ICE(IP 주소)와 자막 원문·번역을 남기지 않는다.
# ---------------------------------------------------------------------------
CLOSE_BUSY = 4409
# 프레임 하나의 최대 크기(UTF-8 바이트). SDP 한 개가 수 KB다.
MAX_CALL_FRAME = 16 * 1024
_CALL_IN: TypeAdapter[CallIn] = TypeAdapter(CallIn)


def _caption_frame(caption: Caption) -> dict:
    return {"type": "caption", "caption": caption.model_dump(by_alias=True)}


async def _send_caption(hub: CallHub, case_id: str, caption_id: str, text: str, source: Lang, target: Lang, llm: LLMClient | None) -> None:
    """저장해 둔 번역 전 자막을 옮겨 채우고 양쪽에 보낸다. 근로자 말은 한국어로, 센터 말은 사례 언어로 옮긴다."""
    tr = await translate_line(text, source, target, llm, timeout_s=settings.llm_timeout_s)
    logger.info("call caption translation=%s", tr.status)
    caption = store.set_caption_translation(case_id, caption_id, tr.status, tr.text)
    # 그사이 데모 초기화로 자막이 지워졌으면 보내지 않는다.
    if caption is not None:
        await hub.send(case_id, _caption_frame(caption))


@router.websocket("/cases/{case_id}/call")
async def call(ws: WebSocket, case_id: str, role: str = "", token: str = "") -> None:
    """근로자·센터 통화. 연결 직후 방에 있는 상대(joined)와 이전 자막(history)을 알리고,
    signal은 상대에게만, caption은 저장한 뒤 번역해 양쪽에 보낸다."""
    await ws.accept()
    denied = _chat_denied(ws, case_id, role, token)
    if denied:
        await ws.close(denied)
        return
    me: ChatRole = "center" if role == "center" else "worker"
    hub: CallHub = ws.app.state.call
    if not hub.join(case_id, me, ws):
        await ws.close(CLOSE_BUSY)
        return
    # join과 이전 자막 읽기 사이에 await가 없어야 그 사이 번역된 자막을 놓치거나 두 번 받지 않는다(채팅과 같다).
    history = [c.model_dump(by_alias=True) for c in store.captions(case_id)]
    # 근로자 언어는 클라이언트 값이 아니라 사례의 언어다.
    case_lang = store.get(case_id).language
    source, target = (case_lang, "ko") if me == "worker" else ("ko", case_lang)
    # 자막 번역도 근로자 경로와 같은 호출 제한을 탄다(backlog 20).
    llm: LLMClient | None = ws.app.state.llm_limiter.wrap(getattr(ws.app.state, "llm", None), ws)
    # 번역을 기다리는 동안에도 시그널링을 계속 중계하도록 자막은 따로 돌린다. 값은 그 작업이 채울 자막 번호다.
    tasks: dict[asyncio.Task, str] = {}
    try:
        await ws.send_json({"type": "joined", "role": me, "peers": hub.peers(case_id, me)})
        await ws.send_json({"type": "history", "captions": history})
        await hub.send(case_id, {"type": "peer", "role": me, "present": True}, exclude=me)
        while True:
            message = await ws.receive()
            if message["type"] == "websocket.disconnect":
                break
            raw = message.get("text") or ""
            try:
                if len(raw.encode()) > MAX_CALL_FRAME:
                    raise ValueError
                frame = _CALL_IN.validate_json(raw)
            except (ValueError, ValidationError):
                await ws.send_json(INVALID_FRAME)
                continue
            if isinstance(frame, CallCaptionIn):
                # 번호·시각은 받은 순서대로 먼저 정한다. 번역이 거꾸로 끝나도 history는 말한 순서다.
                caption_id = store.add_caption(case_id, me, frame.text, source, target, clock.now())
                task = asyncio.create_task(_send_caption(hub, case_id, caption_id, frame.text, source, target, llm))
                tasks[task] = caption_id
                task.add_done_callback(lambda t: tasks.pop(t, None))
            else:
                await hub.send(case_id, {"type": "signal", "from": me, "data": frame.data}, exclude=me)
    except WebSocketDisconnect:
        pass
    finally:
        unfinished = list(tasks.values())
        for task in list(tasks):
            task.cancel()
        left = hub.leave(case_id, me, ws)
        # 번역 중에 끊긴 자막은 원문만 남기고(skipped) 남은 쪽에 보낸다. 그사이 번역을 채운 자막은 None이라 두 번 보내지 않는다.
        caption_frames = [_caption_frame(c) for i in unfinished if (c := store.set_caption_translation(case_id, i, "skipped", None))]
        # 연결이 취소로 끝나도(서버 쪽 정리) 남은 쪽에 알리도록 보내기는 취소에서 막는다.
        with anyio.CancelScope(shield=True):
            for frame in caption_frames:
                await hub.send(case_id, frame)
            if left:
                await hub.send(case_id, {"type": "peer", "role": me, "present": False})


# ---------------------------------------------------------------------------
# C-03 통계: 익명 집계만 돌려주고 5건 미만 칸은 서버에서 가린다(개인 단위 기록을 내보내지 않는다).
# ---------------------------------------------------------------------------
MIN_CELL = 5


def _mask(n: int) -> int | None:
    return n if n >= MIN_CELL else None


def _count_by[K](recs: list[StatRecord], keys: list[K], get: Callable[[StatRecord], K]) -> list[StatCell]:
    return [StatCell(key=str(k), n=_mask(sum(1 for r in recs if get(r) == k))) for k in keys]


STATS_DAYS = (30, 90, 180)


@router.get("/stats", dependencies=staff_only)
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
