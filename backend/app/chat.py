# 상담 채팅(backlog 14)의 열린 연결. 사례 하나가 방 하나다.
# 메시지·토큰은 저장소(store.py)에 두고, 여기에는 지금 붙어 있는 WebSocket만 둔다. 프로세스 하나 기준이다(다중 프로세스 중계는 범위 밖).

from starlette.websockets import WebSocket

# 데모 초기화로 방이 비었을 때 닫는 코드(4000~4999는 앱이 쓰는 범위)
CLOSE_RESET = 4000


class ChatHub:
    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = {}

    def join(self, case_id: str, ws: WebSocket) -> None:
        self._rooms.setdefault(case_id, set()).add(ws)

    def leave(self, case_id: str, ws: WebSocket) -> None:
        room = self._rooms.get(case_id)
        if room is None:
            return
        room.discard(ws)
        if not room:
            del self._rooms[case_id]

    async def broadcast(self, case_id: str, frame: dict) -> None:
        """같은 방의 모든 연결에 보낸다. 이미 끊긴 연결은 건너뛰고 방에서 뺀다."""
        for ws in list(self._rooms.get(case_id, ())):
            try:
                await ws.send_json(frame)
            except Exception:
                self.leave(case_id, ws)

    async def close_all(self, code: int = CLOSE_RESET) -> None:
        rooms, self._rooms = self._rooms, {}
        for room in rooms.values():
            for ws in room:
                try:
                    await ws.close(code)
                except Exception:
                    pass
