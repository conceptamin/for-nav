# 18. 통화 자막 저장과 다시 보기(history)

상태: 완료
의존: 16-call-translation(통화 신호·자막 번역), 07(SQLite 저장소)

## 목표
통화 자막을 사례별로 저장해, 근로자·센터가 통화 화면에 다시 들어오거나 새로고침해도 이전 통화 자막을 번역과 함께 다시 보게 한다. 16은 자막을 저장하지 않아 화면을 떠나면 자막이 사라진다(frontend 26 `## 결과` "자막 기록", 사용자 결정 2026-10-31). 상담 내용 확인은 센터 C-02의 주된 쓰임이므로 채팅 메시지(14)와 같은 방식으로 남긴다. 옛 초안 `16-call-captions.md`의 결정 3-A(사례별 저장)를 지금 계약(16)에 맞게 다시 쓴 것이다.

## 범위
- 하는 것
  - 저장: `CenterStore`에 자막 세 메서드를 더하고 `MemoryStore`·`SqliteStore` 둘 다 구현한다
    - `add_caption(case_id, sender, text, lang, translated_lang, at) -> str`: 받은 순서대로 번호를 정해 `c-<n>`을 돌려준다. 번역 전 상태로 저장한다
    - `set_caption_translation(case_id, caption_id, translation: TranslationStatus, translated: str | None) -> Caption`: 번역이 끝나면 채운다
    - `captions(case_id) -> list[Caption]`: 번역이 끝난 자막만 번호 순서로 돌려준다(번역 전은 아직 양쪽에 보내지 않은 것이라 뺀다)
    - SQLite 표 `call_captions`(`case_id`, `n`, `sender`, `text`, `lang`, `translated`, `translated_lang`, `translation`(NULL = 번역 전), `at`, 기본 키 `(case_id, n)`). `reset()`이 비운다
  - `routers/center.py`의 `_send_caption`: 받자마자 `add_caption`으로 번호·시각을 정하고, 번역 뒤 `set_caption_translation` → 지금처럼 양쪽에 `caption`. 번호는 `CallHub.next_caption_id`(메모리 카운터) 대신 저장소가 정하므로 서버를 다시 띄워도 이어진다. `CallHub`의 자막 카운터는 지운다
  - 번역 작업이 취소되면(말한 쪽 연결이 끊김) 그 자막을 `skipped`, `translated: null`로 채운다. 원문을 잃지 않고 다음 연결의 `history`에 나온다. 취소된 자막은 그때 방에 남은 쪽에도 `caption`으로 보낸다
  - `history` 프레임: `/call` 연결 직후 `joined` 다음에 `{ "type": "history", "captions": [Caption, ...] }`를 한 번 보낸다. 채팅(14)처럼 다시 붙을 때마다 전체를 다시 준다. join과 목록 읽기 사이에 `await`를 두지 않는다(14의 규칙, 그 사이 자막을 놓치거나 두 번 받지 않게)
  - `POST /api/center/reset`이 자막도 비운다(지금처럼 통화 연결은 4000으로 닫는다)
  - `tests/test_store.py`(두 저장소)·`tests/test_call.py`에 아래 완료 기준
  - `README.md`: `/call` 프레임 예시에 `history`, "나중에 붙일 자리"의 "통화 기록" 행(목업 동작을 "자막을 사례별로 저장, 음성은 저장하지 않음"으로), 폴더 구조 표의 테스트 설명
  - `16-call-translation.md` `## 메모`에 "자막 저장은 18이 바꾼다" 한 줄
- 하지 않는 것
  - 음성 저장·녹음. 음성은 계속 서버를 지나지 않는다
  - 보존 기간·자동 삭제·암호화·자막 기록 동의(채팅 메시지와 같이 미결, README "나중에 붙일 자리")
  - 자막을 REST로 내보내는 경로(`GET …/captions`). 통화 패널은 이미 `/call`에 붙어 있으므로 `history`로 충분하다
  - 말하는 중 글 저장. 프론트는 말하는 중 글과 확정 문장을 `signal.data`(`{ speech }`)로 상대에게만 보내고 서버는 열어 보지 않는다. 그대로 둔다
  - 프론트 코드. `useCall`이 `history`를 받아 목록을 통째로 바꾸는 일은 frontend 새 항목으로 따로 한다(`## 메모`)

## API·파일

### 바뀌는 프레임
```jsonc
// 서버 → 클라이언트, 연결 직후 joined 다음에 한 번
{ "type": "history", "captions": [
    { "id": "c-1", "from": "worker", "text": "Tay tôi vẫn còn chảy máu", "lang": "vi",
      "translated": "손에서 아직 피가 납니다", "translatedLang": "ko", "translation": "ok",
      "at": "2026-10-30T05:12:00.000Z" } ] }
```
- `Caption` 형태는 16 그대로다. 번역 전 자막은 `history`에 없다
- 나머지 프레임(`joined`·`peer`·`signal`·`caption`·`error`)과 닫힘 코드는 바뀌지 않는다. 지금 프론트(frontend 26)는 모르는 `type`을 무시하므로 이 항목이 먼저 병합돼도 깨지지 않는다

### 파일
- 수정: `app/store.py`(Protocol·`MemoryStore`), `app/store_sqlite.py`(표·메서드), `app/chat.py`(`CallHub` 자막 카운터 제거), `app/routers/center.py`(`_send_caption`, `history`, 취소 처리), `tests/test_store.py`, `tests/test_call.py`, `README.md`, `backlog/16-call-translation.md`(메모 한 줄)
- 새 모듈·의존성 없음

## 완료 기준
- [x] `uv run ruff check . && uv run ruff format --check .` 통과, `uv run pytest` 통과(네트워크 없이). 기존 테스트는 그대로 통과한다
- [x] `test_store.py`(메모리·SQLite 둘 다): `add_caption` 번호가 사례마다 `c-1`, `c-2`…, 번역 전 자막은 `captions`에 없고 `set_caption_translation` 뒤에 나온다, `reset()` 뒤 비어 있다. SQLite는 저장소를 닫고 다시 열어도 자막과 다음 번호가 이어진다
- [x] `test_call.py`
  - 연결 직후 `joined` 다음 프레임이 `history`이고, 처음에는 빈 목록이다
  - 근로자 자막(가짜 LLM)이 번역된 뒤 센터가 새로 붙으면 `history`에 그 자막이 번역과 함께 있다
  - 번역이 멈춘 동안(가짜 LLM이 기다림) 새로 붙은 쪽의 `history`에는 그 자막이 없고, 번역이 끝나면 `caption`으로 한 번 받는다(두 번 받지 않는다)
  - 말한 쪽이 번역 중에 끊기면 그 자막이 `skipped`로 저장되고 남은 쪽이 `caption`을 받는다
  - 두 자막의 번역이 거꾸로 끝나도 `history`는 말한 순서(`c-1`, `c-2`)다
  - `POST /api/center/reset` 뒤 다시 붙으면 `history`가 비어 있고 번호가 `c-1`부터다
  - 로그(`caplog`)에 자막 원문·번역이 없다(16 기준 그대로)
- [x] `DB_PATH`를 주고 실제 서버를 띄워 Python `websockets` 클라이언트로 자막 두 줄을 보낸 뒤 서버를 다시 띄우고 다시 붙어 `history`에 두 줄이 번역과 함께 있는지 확인하고 `## 결과`에 적는다
- [x] `README.md` 프레임 예시·"나중에 붙일 자리"가 바뀐다

## 결과

### 문서에서 바꾼 점
- `set_caption_translation`은 `Caption`이 아니라 `Caption | None`을 돌려준다. 번역 전 자막만 채우고, 그런 자막이 없으면(데모 초기화로 지워졌거나 이미 채웠으면) None이다. 같은 파일의 `set_status`가 `CenterCase | None`인 것과 같다. 이 None 덕분에 (1) 초기화 뒤 늦게 끝난 번역이 지워진 자막을 되살리거나 보내지 않고, (2) 끊긴 쪽 정리와 번역 완료가 겹쳐도 `caption`이 두 번 가지 않는다
- `add_caption`은 `_send_caption` 안이 아니라 `/call` 수신 반복문에서 프레임을 받자마자 부른다. 번역 task가 시작되기 전에 취소돼도(받자마자 끊김) 자막이 저장돼 있고, 번호가 받은 순서대로 정해진다. `_send_caption`은 번역 → `set_caption_translation` → 양쪽 `caption`만 한다
- 취소된 자막의 처리는 번역 task 안이 아니라 연결의 `finally`에서 한다. 연결마다 남은 task와 그 자막 번호를 들고 있다가, task를 취소하고 방에서 나간 뒤 `skipped`로 채워 남은 쪽에 보낸다. 그 뒤에 `peer present: false`를 보낸다
- `finally`의 보내기(끊긴 쪽 자막, `peer present: false`)는 `anyio.CancelScope(shield=True)` 안에서 한다. 연결이 취소로 끝나면(TestClient가 연결을 닫을 때, 서버 쪽 정리) 첫 `await`에서 다시 취소돼 남은 쪽이 못 받았다. `anyio`는 Starlette가 이미 쓰는 의존성이라 `pyproject.toml`·`uv.lock`은 바뀌지 않는다

### 결정
- 메모리 저장소는 사례별 `(Caption, 번역 끝남)` 목록, SQLite는 `call_captions` 표(`translation` NULL = 번역 전)다. 번호는 SQLite가 `MAX(n) + 1`, 메모리가 목록 길이 + 1이다. 다시 띄워도 번호가 이어진다
- `history`는 `hub.join` 바로 뒤, `await` 전에 읽는다(14의 규칙). 그래서 그 사이 번역이 끝난 자막은 `history`에 있거나 `caption`으로 오고, 둘 다 오지는 않는다
- 로그는 그대로 `call caption translation=<상태>`만 남긴다. 끊겨서 `skipped`로 채운 자막은 따로 로그를 남기지 않는다

### 실행
- `uv run ruff check . && uv run ruff format --check .` → All checks passed, 75 files already formatted
- `uv run pytest` → 3028 passed(새 테스트 13개: `tests/test_call.py` +6 — 처음 `history` 빈 목록, 새 연결의 `history`에 번역과 함께, 번역 중 붙은 쪽은 `history`에 없고 `caption` 한 번, 말한 쪽이 끊기면 `skipped` 저장·남은 쪽 `caption`, 번역이 거꾸로 끝나도 `c-1`·`c-2`, 초기화 뒤 빈 `history`·`c-1`부터. `tests/test_store.py` +7 — 메모리·SQLite 각각 번호·번역 전 빼기·번역 전만 채우기·초기화, SQLite 재시작). 기존 `test_call.py` 19개는 연결 직후 `history`를 받도록 도우미(`greet`)만 고쳤다. 로그 테스트(`caplog`에 원문·번역 없음)는 그대로 통과
- `tests/test_call.py`를 5번 다시 돌려 모두 25 passed(시간 제한 0.5초를 쓰는 테스트가 흔들리지 않는지)
- 실제 서버(완료 기준, Python `websockets` 17.3 클라이언트, 스크립트는 저장소 밖에 두었다)
  - `DB_PATH=<임시 폴더>/live.db uv run --env-file <backend/.env> fastapi run app/main.py --port 8765` (`claude-haiku-5-5`)
  - 사례 `C-93510` 생성 → 근로자·센터 모두 `joined` 다음 `history` `[]`
  - 근로자 "Tay tôi vẫn còn chảy máu"(`c-1`), 센터 "언제부터 피가 났나요?"(`c-2`) → 번역이 `c-2`, `c-1` 순서로 끝났다(둘 다 `ok`)
  - 서버를 끄고 같은 `DB_PATH`로 다시 띄운 뒤 센터로 다시 붙음 → `history`가 `c-1`("제 손이 아직도 피가 나고 있어요"), `c-2`("Bạn bị chảy máu từ khi nào?") 순서, 둘 다 `translation: "ok"`
  - `sqlite3 live.db "select case_id,n,sender,translation from call_captions"` → `C-93510|1|worker|ok`, `C-93510|2|center|ok`
  - 두 서버 로그에서 자막 원문·번역·`token=`이 든 줄 0개. 남은 줄은 `call caption translation=ok` 2줄과 `app.access WS /api/center/cases/C-93510/call 1000 …ms request_id=…`

### 바뀐 API
- `WS /api/center/cases/{id}/call`: 연결 직후 `joined` 다음에 `{ "type": "history", "captions": [Caption, ...] }`를 한 번 보낸다. 다른 프레임·닫힘 코드는 그대로다
- `Caption.id`(`c-<n>`)는 서버를 다시 띄워도 이어진다(`DB_PATH`가 있을 때). 데모 초기화 때는 처음부터다
- `POST /api/center/reset`이 통화 자막도 지운다

### 남은 문제
- 프론트가 `history`를 받아 쓰는 일은 아래 메모의 frontend 항목이다. 지금 프론트(frontend 26)는 모르는 `type`을 무시해 깨지지 않는다
- 번역 중에 서버 프로세스가 죽으면 그 자막은 번역 전(NULL)으로 남아 `history`에 계속 나오지 않는다(아래 메모)

## 메모
- 프론트 후속(frontend 새 항목): `src/api/call.ts`의 `useCall`이 `history`를 받으면 `captions`를 통째로 바꾸고(채팅 `useChat`과 같음, 다시 붙을 때 겹치지 않게), C-02 통화 안내 문구의 "자막은 이 화면을 떠나면 사라집니다(서버에 저장하지 않음)"와 frontend `README.md`의 "화면 메모리" 행·"나중에 붙일 자리"의 통화 자막 기록 행을 고친다. frontend 26 `## 완료 기준`의 "새로고침해도 자막이 다시 보인다"가 그때 살아난다
- 자막은 자유 발화라 이름·증상·연락처 같은 개인 정보가 들어간다. 채팅 메시지와 같은 저장소·같은 미결 상태로 두고, 보존 기간을 정할 때 채팅과 함께 정한다
- 번역 시도 횟수·시간 제한·guard(`check_ko_text`)는 16 그대로다. 저장은 번역 결과를 바꾸지 않는다
- 번역 중에 서버 프로세스가 죽으면 그 자막은 번역 전으로 남는다. 시작할 때 번역 전 자막을 `skipped`로 바꾸면 원문이 `history`에 나온다. 필요하면 새 항목으로 한다(서버 시작 시 저장소 정리)
