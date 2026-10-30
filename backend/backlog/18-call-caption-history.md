# 18. 통화 자막 저장과 다시 보기(history)

상태: 대기
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
- [ ] `uv run ruff check . && uv run ruff format --check .` 통과, `uv run pytest` 통과(네트워크 없이). 기존 테스트는 그대로 통과한다
- [ ] `test_store.py`(메모리·SQLite 둘 다): `add_caption` 번호가 사례마다 `c-1`, `c-2`…, 번역 전 자막은 `captions`에 없고 `set_caption_translation` 뒤에 나온다, `reset()` 뒤 비어 있다. SQLite는 저장소를 닫고 다시 열어도 자막과 다음 번호가 이어진다
- [ ] `test_call.py`
  - 연결 직후 `joined` 다음 프레임이 `history`이고, 처음에는 빈 목록이다
  - 근로자 자막(가짜 LLM)이 번역된 뒤 센터가 새로 붙으면 `history`에 그 자막이 번역과 함께 있다
  - 번역이 멈춘 동안(가짜 LLM이 기다림) 새로 붙은 쪽의 `history`에는 그 자막이 없고, 번역이 끝나면 `caption`으로 한 번 받는다(두 번 받지 않는다)
  - 말한 쪽이 번역 중에 끊기면 그 자막이 `skipped`로 저장되고 남은 쪽이 `caption`을 받는다
  - 두 자막의 번역이 거꾸로 끝나도 `history`는 말한 순서(`c-1`, `c-2`)다
  - `POST /api/center/reset` 뒤 다시 붙으면 `history`가 비어 있고 번호가 `c-1`부터다
  - 로그(`caplog`)에 자막 원문·번역이 없다(16 기준 그대로)
- [ ] `DB_PATH`를 주고 실제 서버를 띄워 Python `websockets` 클라이언트로 자막 두 줄을 보낸 뒤 서버를 다시 띄우고 다시 붙어 `history`에 두 줄이 번역과 함께 있는지 확인하고 `## 결과`에 적는다
- [ ] `README.md` 프레임 예시·"나중에 붙일 자리"가 바뀐다

## 결과
(구현 후 작성)

## 메모
- 프론트 후속(frontend 새 항목): `src/api/call.ts`의 `useCall`이 `history`를 받으면 `captions`를 통째로 바꾸고(채팅 `useChat`과 같음, 다시 붙을 때 겹치지 않게), C-02 통화 안내 문구의 "자막은 이 화면을 떠나면 사라집니다(서버에 저장하지 않음)"와 frontend `README.md`의 "화면 메모리" 행·"나중에 붙일 자리"의 통화 자막 기록 행을 고친다. frontend 26 `## 완료 기준`의 "새로고침해도 자막이 다시 보인다"가 그때 살아난다
- 자막은 자유 발화라 이름·증상·연락처 같은 개인 정보가 들어간다. 채팅 메시지와 같은 저장소·같은 미결 상태로 두고, 보존 기간을 정할 때 채팅과 함께 정한다
- 번역 시도 횟수·시간 제한·guard(`check_ko_text`)는 16 그대로다. 저장은 번역 결과를 바꾸지 않는다
