# 30. 상담 채팅 메시지 번역

상태: 완료
의존: 14(상담 채팅), 16(통화 자막 번역), 20(LLM 호출 제한)

## 목표
근로자는 모국어로, 상담자는 한국어로 채팅해도 서로 읽을 수 있게 메시지마다 상대 언어 번역을 붙인다. 지금은 README "나중에 붙일 자리"대로 원문만 주고받아(14), 근로자 화면 안내도 "번역 없이 보낸다"고 적혀 있다. 통화 자막(16·18)과 같은 번역 함수·같은 필드 모양을 써서 프론트가 말풍선 하나에 원문과 번역을 함께 보이게 한다.

## 범위
- 하는 것
  - 번역 시점: 받은 메시지를 **저장·방송하기 전에** 번역한다. 번역이 끝난 메시지 하나를 지금처럼 `message` 프레임으로 한 번 보낸다. 번역 전 상태·고쳐 보내는 프레임이 없어 읽음(28)·`history`·번호 규칙이 그대로다. 보낸 사람에게도 번역 시간(한 번 호출, `LLM_TIMEOUT_S` 이내)만큼 늦게 되돌아간다
  - 방향: 근로자 메시지는 사례 언어 → 한국어, 센터 메시지는 한국어 → 사례 언어(통화 자막과 같다). 사례 언어가 `ko`면 부르지 않는다(`skipped`)
  - 번역 함수: `templates/translate.py`에 `translate_message(text, source, target, client, timeout_s)`. 통화 자막 `translate_line`과 같이 한 번만 부르고(재시도·역번역 없음), 한국어 쪽은 `check_ko_text`로 검사한다. 프롬프트만 채팅용(받아쓰기 오류 문장 대신 "채팅 메시지")이다
  - 실패하면 원문만 보낸다: LLM 없음·호출 실패·시간 초과는 `skipped`, guard 탈락은 `rejected`, 둘 다 `translated: null`. LLM 실패가 채팅 실패가 되지 않는다
  - 호출 제한: 통화 자막처럼 `app.state.llm_limiter.wrap(...)`으로 감싼다(20). 제한에 걸리면 `skipped`
  - `ChatMessage`에 선택 필드 넷을 더한다(`Caption`과 같은 이름·뜻): `lang`, `translated`, `translatedLang`, `translation`. 이 항목 전에 저장된 메시지는 넷 다 `null`이다
  - 저장: `CenterStore.add_message`가 번역 결과를 함께 받는다. 메모리·SQLite 둘 다. SQLite는 `chat_messages`에 열 넷(`lang`, `translated`, `translated_lang`, `translation`, 모두 NULL 허용)을 더하고, 이미 있는 DB 파일은 시작할 때 없는 열만 `ALTER TABLE … ADD COLUMN`으로 더한다
  - 로그: `chat translation=<상태>`만 남긴다. 원문·번역은 남기지 않는다(14·16 기준 그대로)
  - `README.md`: `/chat` 프레임 예시, "나중에 붙일 자리"의 "상담 채팅 번역" 행, 폴더 구조 표의 `translate.py`·`test_chat.py` 설명
- 하지 않는 것
  - 역번역 검사(리포트 `note`처럼 세 번 부르기). 채팅은 대화라 늦으면 쓸모가 줄어 통화 자막과 같이 한 번만 부른다(`## 메모`)
  - 원문을 먼저 보내고 번역을 나중에 채우는 방식(새 프레임, 번역 전 상태)
  - 근로자가 사례 언어가 아닌 언어로 쓴 경우의 언어 감지. 사례 언어로 쓴다고 보고 옮긴다(LLM이 대체로 알아서 옮긴다)
  - 프론트 코드. 말풍선에 번역 표시, `chatIntro` 문구 변경은 frontend 새 항목으로 따로 한다(`## 메모`)

## API·파일

### 바뀌는 프레임
```jsonc
// 서버 → 클라이언트: 새 메시지(history의 messages도 같은 모양)
{ "type": "message", "message": { "id": "m-1", "caseId": "C-47625", "from": "worker", "text": "Tay tôi vẫn còn chảy máu",
  "lang": "vi", "translated": "손에서 아직 피가 납니다", "translatedLang": "ko", "translation": "ok",
  "at": "2026-10-30T11:50:47.646Z" } }
```
- 새 필드는 모두 선택이다. 지금 프론트는 `id`·`from`·`text`·`at`만 보므로 이 항목이 먼저 병합돼도 깨지지 않는다
- 클라이언트 → 서버 프레임, `read`·`error` 프레임, 닫힘 코드는 바뀌지 않는다

### 파일
- 수정: `app/schemas.py`(`ChatMessage`), `app/templates/translate.py`(`translate_message`), `app/store.py`(Protocol·`MemoryStore`·`make_message`), `app/store_sqlite.py`(열·`ALTER`·메서드), `app/routers/center.py`(`chat`), `tests/test_chat.py`, `tests/test_store.py`, `tests/test_translation.py`, `README.md`
- 새 모듈·의존성 없음

## 완료 기준
- [x] `uv run ruff check . && uv run ruff format --check .` 통과, `uv run pytest` 통과(네트워크 없이). 기존 테스트는 그대로 통과한다
- [x] `test_translation.py`: `translate_message`가 같은 언어·LLM 없음·호출 실패면 `skipped`, 한국어 번역이 guard에 걸리면 `rejected`, 성공하면 `ok`와 번역문
- [x] `test_chat.py`(메모리·SQLite)
  - LLM이 없으면 메시지가 `translation: "skipped"`, `translated: null`, `lang`·`translatedLang`이 사례 언어·`ko`로 지금처럼 바로 온다
  - 근로자 메시지(가짜 LLM)가 한국어 번역과 함께 양쪽에 오고, 센터 메시지는 사례 언어 번역과 함께 온다. 다시 붙으면 `history`에 번역이 그대로 있다
  - LLM 호출 실패면 `skipped`, guard 탈락이면 `rejected`이고 원문은 그대로 온다
  - 로그(`caplog`)에 메시지 원문·번역이 없다
- [x] `test_store.py`: 이 항목 전 모양의 `chat_messages` 표가 있는 SQLite 파일을 열면 열이 더해지고, 옛 메시지는 새 필드가 `null`로 읽힌다
- [x] 실제 서버(`--env-file`로 LLM 키)를 띄워 Python `websockets` 클라이언트로 근로자 베트남어 한 줄, 센터 한국어 한 줄을 보내 서로의 번역이 오는지 확인하고 `## 결과`에 적는다
- [x] `README.md` 프레임 예시·"나중에 붙일 자리"가 바뀐다

## 결과

### 문서에서 바꾼 점
- `CenterStore.add_message`는 번역 필드 넷을 따로 받지 않고 선택 인자 `translation: MessageTranslation | None`(`store.py`의 frozen dataclass) 하나로 받는다. 넘기지 않으면 넷 다 None이라 기존 호출(테스트)이 그대로 돈다
- `translate_message`와 `translate_line`은 같은 몸통(`_translate_once`)을 쓰고 프롬프트만 다르다. 채팅 프롬프트에는 "이름·숫자·날짜·주소·전화번호는 쓴 그대로"를 더했다(받아쓰기 오류 문장 안내는 뺐다)

### 결정
- 번역 시점·방식은 사용자 확인대로 "번역 뒤 한 번에 보내기", "한 번 호출"이다(2026-10-31)
- 필드 이름은 README의 `textKo` 대신 `Caption`과 같은 넷으로 했다(`## 메모` 첫 줄, 사용자 확인). README "나중에 붙일 자리" 행을 함께 고쳤다
- SQLite는 `chat_messages`에 NULL 허용 열 넷을 더하고, 열 때 `PRAGMA table_info`로 없는 열만 `ALTER TABLE … ADD COLUMN`한다. 운영 DB(app.for-nav.com)도 서버를 다시 띄우면 그대로 이어진다. 별도 마이그레이션 도구는 두지 않았다(지금 표 하나, 열 넷)
- 번역은 연결의 수신 반복문 안에서 기다린다. 그동안 같은 연결의 다음 프레임(읽음 포함)은 번역이 끝난 뒤 처리된다. 다른 연결(상대)은 막히지 않는다. 두 사람이 거의 동시에 보내면 번역이 먼저 끝난 쪽이 앞 번호를 받는다
- 호출 제한(20)은 통화 자막과 같이 `llm_limiter.wrap`으로 탄다

### 실행
- `uv run ruff check . && uv run ruff format --check .` → All checks passed, 91 files already formatted
- `uv run pytest` → 2891 passed(기준 `origin/main` 2873 → 새 테스트 18개)
  - `tests/test_chat.py` +10(메모리·SQLite 각각): 양방향 번역과 다시 붙을 때 `history`, 프롬프트 언어 방향, LLM 없음·호출 실패 `skipped`·guard `rejected`에서 원문만, 로그에 원문·번역 없음. 기존 두 테스트는 메시지 전체 비교에 새 필드를 넣거나 필요한 필드만 비교하도록 고쳤다
  - `tests/test_store.py` +3: 번역 저장·읽기(메모리·SQLite), 번역 열이 없는 옛 SQLite 파일을 열면 열이 더해지고 옛 메시지는 `null`, 두 번째로 열어도 괜찮다. 기존 메시지 비교 하나에 None 필드를 넣었다
  - `tests/test_translation.py` +5: `translate_message` 성공(채팅 프롬프트), 같은 언어·LLM 없음·호출 실패 `skipped`, guard `rejected`
- 실제 서버(`DB_PATH=<임시 폴더>/live.db uv run --env-file backend/.env fastapi run app/main.py --port 8766`, `claude-haiku-5-5`), Python `websockets` 17.3 클라이언트(스크립트는 저장소 밖)
  - 사례 `C-52946`(vi) 생성, 근로자·센터 연결
  - 근로자 "Tay tôi vẫn còn chảy máu từ sáng nay" → 1.21초 뒤 양쪽에 `translated: "오늘 아침부터 아직도 손에서 피가 나고 있어요."`, `vi → ko`, `ok`
  - 센터 "언제부터 피가 났나요? 사진을 보내 주세요." → 2.09초 뒤 양쪽에 `translated: "Bạn bị chảy máu từ khi nào? Vui lòng gửi cho tôi một tấm ảnh."`, `ko → vi`, `ok`
  - 다시 붙은 센터의 `history`: `m-1`·`m-2` 둘 다 `ok`. `sqlite3 live.db` → 두 행에 `lang`·`translated_lang`·`translation`이 채워져 있다
  - 서버 로그에 원문·번역·`token=`이 든 줄 0개. 남은 줄은 `chat translation=ok` 2줄과 `app.access WS …/chat 1000 …`

### 바뀐 API
- `ChatMessage`(`/chat`의 `history`·`message` 프레임)에 선택 필드 `lang`, `translated`, `translatedLang`, `translation`. 다른 프레임·닫힘 코드는 그대로다
- 메시지가 번역 시간만큼(실측 1~2초, 최대 `LLM_TIMEOUT_S`) 늦게 되돌아온다

### 남은 문제
- 프론트가 번역을 보여 주는 일은 아래 메모의 frontend 항목이다. 지금 프론트는 새 필드를 무시해 깨지지 않지만, 보낸 뒤 1~2초 동안 말풍선이 뜨지 않는다

## 메모
- README "나중에 붙일 자리"는 `textKo`·`translation` 두 필드를 적었지만, 센터 메시지는 한국어 → 근로자 언어로 옮기므로 `textKo`가 맞지 않는다. 통화 자막 `Caption`(16·18)과 같은 `lang`·`translated`·`translatedLang`·`translation`으로 바꾸고 README 행을 함께 고친다(사용자 확인)
- 리포트 `note`(05)는 의사에게 가는 기록이라 역번역 검사를 했다. 채팅은 상담자가 되물을 수 있는 대화이고 원문을 항상 함께 보이므로 한 번 호출로 둔다. 오역이 문제가 되면 역번역을 더하는 새 항목으로 한다
- 프론트 후속(frontend 새 항목): `ChatMessage` 타입에 선택 필드 넷, `ChatPanel` 말풍선에 `translation === 'ok'`이면 번역문을 크게·원문을 작게(통화 자막 표시와 같게), 보내고 되돌아올 때까지 "번역 중" 표시, 20개 언어 `chatIntro`에서 "번역 없이" 문구를 고친다
