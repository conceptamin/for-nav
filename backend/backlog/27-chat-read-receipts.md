# 27. 상담 채팅 읽음 표시

상태: 완료
의존: 14 상담 채팅. frontend 45(채팅 시트 모양과 읽음 표시)와 한 PR로 낸다

## 목표
2026-10-31 사용자 요청: 상담 채팅에서 상대가 내 글을 읽었는지 보이게 한다. 근로자는 센터가, 센터는 근로자가 어디까지 읽었는지 알아야 하므로 서버가 역할별 "어디까지 읽었다"를 받아 저장하고 방에 알린다. 다시 붙거나 상대가 나중에 들어와도 같은 값을 받도록 연결 직후 `history`에도 싣는다.

## 범위
- 하는 것
  - 클라이언트 → 서버 새 프레임 `{ "type": "read", "upTo": "m-5" }`: 이 연결의 역할이 `m-5`까지 읽었다
    - `upTo`는 이 사례에 있는 메시지 id여야 한다. 없는 id·형식이 틀린 id는 `{ "type": "error", "code": "invalid" }`(연결은 그대로)
    - 저장된 값보다 앞이면(이미 더 읽었으면) 저장도 방송도 하지 않는다
  - 서버 → 클라이언트 새 프레임 `{ "type": "read", "role": "center", "upTo": "m-5" }`: 값이 바뀌면 같은 방의 모든 연결에 보낸다(보낸 쪽 다른 창도 맞춘다)
  - `history` 프레임에 `read` 필드: `{ "type": "history", "messages": [...], "read": { "worker": "m-3", "center": null } }`. 아직 읽은 것이 없으면 `null`
  - 저장소: `mark_read(case_id, role, n) -> bool`(바뀌었으면 True), `read_marks(case_id) -> dict[ChatRole, str | None]`. 메모리 구현은 dict, SQLite 구현은 새 표 `chat_reads(case_id, role, n)`. 데모 초기화가 함께 지운다
  - `schemas.py`: `ChatIn`을 `type`으로 가르는 두 모양(`message`, `read`)으로. `ChatReadIn.up_to`는 `m-<숫자>` 형식
  - 테스트(`tests/test_chat.py`): 읽음이 상대에게 가는지, 다시 붙으면 `history.read`로 오는지, 뒤로 가는 값·없는 id·형식 틀린 id, 데모 초기화 뒤 비는지, SQLite 저장소에서도 남는지
  - `README.md` 채팅 프레임 설명
- 하지 않는 것
  - 메시지별 읽은 시각, 입력 중 표시, 안 읽은 수를 세어 주는 REST 경로
  - 센터 직원 여러 명 구분(센터는 역할 하나로 본다)
  - 통화 자막의 읽음

## 화면·파일
- API: `WS /api/center/cases/{id}/chat` 프레임만 더한다. 닫힘 코드·권한은 그대로
- 파일: `app/schemas.py`, `app/routers/center.py`, `app/store.py`, `app/store_sqlite.py`, `tests/test_chat.py`, `README.md`

## 완료 기준
- [x] `uv run pytest` 통과
- [x] 근로자가 `read`를 보내면 센터 연결이 `{type:"read", role:"worker", upTo}`를 받는다(반대도 같다)
- [x] 끊었다 다시 붙으면 `history.read`에 마지막 값이 있다. 아무도 안 읽었으면 둘 다 `null`
- [x] 더 앞의 id를 보내면 아무 프레임도 오지 않는다. 없는 id·형식 틀린 id는 `error invalid`이고 연결이 남는다
- [x] 데모 초기화 뒤 새 방의 `history.read`가 비어 있다
- [x] 접근 로그에 본문·토큰이 없다(기존 테스트 그대로 통과)

## 결과
- `uv run ruff check . && uv run ruff format --check .` → 통과, `uv run pytest` → 2849 통과(메모리·SQLite 두 저장소)
- 바뀐 API(`WS /api/center/cases/{id}/chat`)
  - 받는 프레임 `{ "type": "read", "upTo": "m-<n>" }` 추가. 이 사례에 없는 메시지(`n`이 메시지 수보다 큼), `m-0`, `c-1` 같은 형식, 숫자 값은 `error invalid`(연결 유지)
  - 보내는 프레임 `{ "type": "read", "role", "upTo" }` 추가(방의 모든 연결). `history`에 `read: { worker, center }` 추가(없으면 `null`)
- 테스트 추가: 읽음이 방에 가고 다시 붙으면 `history.read`로 오는지, 뒤로 가는 값·같은 값은 조용히 무시, 없는 메시지의 읽음, SQLite 파일을 다시 열어도 남고 초기화로 비는지. 잘못된 프레임 목록에 `read` 형식 4개, 초기화 테스트에 읽음을 더했다. 빈 `history` 기대값 4곳에 `read`를 더했다
- 결정
  - 저장소는 역할마다 메시지 번호 하나만 둔다(`mark_read`가 앞으로 옮겨졌을 때만 True). SQLite는 `INSERT … ON CONFLICT DO UPDATE … WHERE excluded.n > chat_reads.n`과 `rowcount`로 한 문장에 끝낸다
  - 자기 글까지 읽음으로 보내는 것도 막지 않는다. 앞뒤만 비교하면 되고 화면이 상대 역할의 값만 쓰기 때문이다
  - `ChatIn`은 `CallIn`처럼 `type`으로 가르는 두 모양이 됐다(`ChatMessageIn`, `ChatReadIn`)

## 메모
- 프론트(frontend 45)는 시트가 열려 있고 화면이 보일 때만 `read`를 보낸다. 숨긴 시트에 붙어 있는 연결은 읽음을 보내지 않는다
- 메시지 id가 사례 안에서 `m-1`, `m-2`…로 늘어나므로 숫자로 앞뒤를 비교한다(`make_message`)
