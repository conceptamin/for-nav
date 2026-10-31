# 28. 근로자 앱 푸시 알림: 기기 토큰 등록과 FCM 발송

상태: 진행 중(코드 완료, 실제 FCM 발송 확인 남음: Firebase 프로젝트·서비스 계정 키와 app-front 07 Android 앱 필요)
의존: 27(`POST /api/center/my-cases`, 채팅 토큰으로 사례를 확인하는 방식). 앱 몫은 app-front 07(호스트 FCM)·08(웹 다리), 근로자 화면 몫은 frontend 48(app-front 08 `## 결정이 필요한 것` 1)

## 목표
센터 회신(2026-10-31)의 지원 절차 마지막 단계는 "상담 결과 안내·사후관리"다. frontend 46·backend 27로 근로자가 앱을 **다시 열면** 요청 상태와 읽지 않은 센터 메시지를 보지만, 앱이 닫혀 있으면 센터가 답하거나 상태를 바꿔도 알 길이 없다. Flutter 앱이 받은 FCM 기기 토큰을 근로자가 가진 사례 채팅 토큰으로 그 사례에 묶어 두고, 센터가 채팅에 글을 쓰거나 상태를 바꾸면 그 기기로 FCM 알림을 보낸다. 서버는 여전히 근로자 계정·회원 정보를 저장하지 않는다(기기 토큰은 계정이 아니라 사례에 묶인다).

## 결정이 필요한 것
권장안으로 적었다. 사용자가 "구현하라"고 해(2026-10-31) 모두 권장대로 정했다.

1. **Firebase 프로젝트와 발송 키를 어디에 두나.** → **권장대로 결정(2026-10-31).**
   - 권장: 근로자 Google 로그인 클라이언트가 있는 **같은 Google Cloud 프로젝트에 Firebase를 붙인다**(프로젝트 하나로 OAuth·FCM을 관리). 서버는 **FCM 발송 권한만 가진 서비스 계정** 키 JSON을 저장소 밖 파일로 두고 경로를 환경 변수(`FCM_CREDENTIALS_FILE`)로 받는다. 맥미니는 `backend/.env`(커밋하지 않음)에 경로를, 키 파일은 `deploy/` 밖 홈 폴더에 둔다. 키는 코드·로그·PR에 넣지 않는다
   - 발송은 FCM HTTP v1(`POST https://fcm.googleapis.com/v1/projects/{FCM_PROJECT_ID}/messages:send`)을 `httpx`로 직접 부른다. 접근 토큰은 이미 의존성에 있는 `google-auth`의 서비스 계정 자격 증명으로 만든다. **`firebase-admin`은 더하지 않는다**(무겁고, 쓰는 것은 발송 한 경로뿐)
   - 대안: 앱 전용 Firebase 프로젝트를 따로 만든다. 콘솔·권한이 둘로 나뉘어 데모 팀에는 관리가 늘어난다
2. **알림 문구의 언어와 내용.** → **권장대로 결정(2026-10-31).**
   - 내용 권장: 제목은 앱 이름 "for nav", 본문은 **"센터에서 새 소식이 있습니다" 한 문장 하나**를 메시지·상태 변경 모두에 쓴다. 공용 휴대폰 잠금 화면에 보이므로 센터 메시지 본문, 상태 이름("완료"), 사례 번호, 이름, "의료·상담" 같은 말을 넣지 않는다. 숫자 배지도 쓰지 않는다
   - 언어 권장: **등록할 때 웹이 근로자의 앱 언어로 번역된 그 한 문장을 같이 보낸다**(`notice`, 80자 이내). 문구의 원본이 `frontend/src/i18n/`에 남고(새 키 하나, frontend 48), 서버는 20개 언어 표를 따로 들고 있지 않는다. 앱 언어를 바꾸면 웹이 다시 등록해 문구가 바뀐다. 서버는 길이·제어 문자만 검사한다. 그 문장은 등록한 기기 자신에게만 가므로 남에게 임의 문구를 보낼 길은 없다
   - 대안 A: 서버가 `CenterCase.language`로 고르는 20개 언어 문구표(`app/templates/push.py`). 프론트 i18n과 두 벌이 되어 동기화 테스트가 하나 더 필요하다
   - 대안 B: 영어·한국어 고정 한 줄. 가장 단순하지만 근로자 대부분이 읽기 어렵다
3. **얼마나 자주 보내나.** → **권장대로 결정(2026-10-31).**
   - 권장: 사례마다 **60초에 한 번까지**만 보낸다(그 사이의 메시지·상태 변경은 건너뛴다). FCM `collapse_key`·Android `tag`·APNs `apns-collapse-id`를 사례 id로 주어 알림 센터에 사례당 한 줄만 남게 한다. 근로자가 그 사례 채팅 WebSocket에 **붙어 있으면 보내지 않는다**(앱을 보고 있다)
   - 대안: 매번 보낸다. 상담 중 센터가 여러 줄을 쓰면 알림이 쏟아진다
4. **"근로자 회원 정보를 저장하지 않는다"(`CLAUDE.md`)와 어떻게 맞추나.** → **권장대로 결정(2026-10-31).**
   - 권장: 기기 토큰은 **사례 id에만** 묶고 계정 키·세션과 잇지 않는다. 저장하는 것은 `(사례 id, 기기 토큰, 플랫폼, notice, 갱신 시각)`뿐이다. 데모 초기화, 근로자의 해제 요청, FCM이 "없는 토큰"이라고 답할 때, **마지막 등록 뒤 30일**이 지나면 지운다(등록·발송 때 함께 정리. 앱을 열 때마다 웹이 다시 등록하므로 쓰는 기기는 계속 남는다). 기기 하나에 사례 20개, 사례 하나에 기기 5개까지
   - 이 결정이 서면 `backend/CLAUDE.md` "서버는 근로자 회원 정보를 저장하지 않는다" 줄에 "푸시 기기 토큰은 사례에만 묶어 30일 보존"을 더한다(이 항목 PR에서)
   - 대안: 기기 토큰을 해시로만 저장. 발송하려면 원래 토큰이 있어야 하므로 쓸 수 없다
5. **iOS 발송(APNs).** → **권장대로 결정(2026-10-31).** iOS는 FCM이 APNs로 넘기므로 Firebase 콘솔에 APNs 인증 키(.p8)를 올려야 하고, 그 키는 유료 Apple Developer 계정에서만 만든다. 서버 코드는 플랫폼과 관계없이 같다. 권장: 이 항목은 Android로 완료를 확인하고, iOS는 키가 준비되면 같은 서버로 확인한다(app-front 07 결정 3)

## 범위
- 하는 것
  - **기기 등록** `POST /api/center/push-devices`
    - 요청: `{ "deviceToken": "…", "platform": "android" | "ios", "notice": "센터에서 새 소식이 있습니다", "cases": [{ "id": "C-…", "token": "…" }] }`. `cases`는 1~20개(27과 같은 경계). `deviceToken`은 4096자 이내
    - 채팅 토큰이 맞는 사례에만 묶는다(`secrets.compare_digest`). **틀린 토큰·없는 사례는 오류 없이 빠진다**(27과 같이 사례 존재 여부를 드러내지 않는다)
    - 응답: `{ "cases": ["C-…"] }`(묶인 사례 id). 같은 기기·사례를 다시 보내면 `notice`·`platform`·갱신 시각만 바뀐다
    - `WORKER_AUTH=google`이면 `require_worker`(27과 같다), `off`면 채팅 토큰만 본다
  - **기기 해제** `POST /api/center/push-devices/remove`: `{ "deviceToken": "…" }` → 그 기기의 묶음을 모두 지운다. `204`. 없는 토큰도 `204`. 근로자 로그아웃·계정 바꾸기·"내 데이터 지우기" 때 웹이 부른다
  - **발송 시점**
    - 채팅 WebSocket에서 **센터**가 글을 썼을 때(`sender == "center"`). 근로자 글은 보내지 않는다
    - `PATCH /api/center/cases/{id}`로 상태가 **실제로 바뀌었을 때**. 같은 값으로 다시 PATCH하면 보내지 않는다
    - 결정 3의 60초 제한·접속 중 건너뛰기
  - **발송은 요청을 늦추거나 실패시키지 않는다.** 채팅·PATCH 응답을 먼저 끝내고 발송은 백그라운드 작업으로 돌린다(시간 제한 5초, 재시도 없음). 실패는 로그에 종류(예외 이름, HTTP 상태)만 남긴다. FCM이 `UNREGISTERED`(404)·토큰 형식 오류(400 `INVALID_ARGUMENT`)로 답하면 그 기기 토큰을 지운다
  - **FCM 메시지 모양**: `notification { title: "for nav", body: <notice> }`, `data { kind: "center", caseId }`, `android { collapse_key: caseId, notification { tag: caseId } }`, `apns { headers { apns-collapse-id: caseId } }`. 메시지 본문·상태 이름은 `data`에도 넣지 않는다. 앱은 `caseId`만으로 시트를 연다(app-front 07)
  - `app/push.py`(새): `PushSender` 프로토콜(`send(device_token, platform, title, body, data, collapse) → None`, 실패는 `PushError(kind)`), `FcmSender`(google-auth 자격 증명 + httpx, 접근 토큰은 만료 전까지 메모리에 둔다), 설정이 없으면 발송기 없음(아무것도 보내지 않는다). `llm.py`·`mail.py`와 같은 모양
  - `app/settings.py`: `PUSH`(`off` 기본 | `fcm`), `FCM_PROJECT_ID`, `FCM_CREDENTIALS_FILE`. `fcm`인데 둘 중 하나가 없거나 파일을 못 읽으면 시작할 때 경고 한 줄을 남기고 `off`처럼 동작한다(키 없이도 서버가 뜬다, LLM과 같은 원칙)
  - `app/store.py`·`app/store_sqlite.py`: `add_push_device`, `push_devices(case_id)`, `remove_push_device(device_token)`, 30일 정리, `reset()`에서 함께 지우기. SQLite 표 `push_devices(case_id, device_token, platform, notice, updated_at, PRIMARY KEY(case_id, device_token))`
  - `app/chat.py`: 사례 방에 근로자 연결이 있는지 묻는 함수(결정 3)
  - `app/schemas.py`: `PushDeviceRequest`, `PushDeviceResponse`, `PushDeviceRemove`
  - `tests/fakes.py`: `FakePushSender`(보낸 것을 목록에 쌓는다, 지정한 토큰은 `UNREGISTERED`로 실패). **테스트는 네트워크 없이 가짜 발송기로만 돈다.** `FcmSender`는 가짜 전송(`httpx.MockTransport`)과 테스트용 서비스 계정 키로 요청 모양만 확인한다
  - `README.md`: API 표·요청·응답 예시, 환경 변수 표, 폴더 구조(`push.py`, `test_push.py`), "나중에 붙일 자리"의 푸시 줄, 맥미니 배포에 키 파일 두는 곳
- 하지 않는 것
  - 통화가 걸려 올 때의 알림(전화처럼 울리기, iOS CallKit·Android 전체 화면 알림). app-front README "나중에 붙일 자리"의 "센터가 걸 때 알림"은 따로 한다(메모)
  - 웹 푸시(브라우저 Service Worker + VAPID). 단독 웹앱(`www.for-nav.com`)은 지금처럼 앱을 다시 열 때 15초 주기로 읽는다(app-front 08 결정 4)
  - 알림 문구에 메시지 내용·상태·이름 넣기, 읽지 않은 수 배지
  - 근로자 계정에 기기 묶기, 기기 사이 동기화
  - 센터 화면 변경(누가 알림을 받는지 센터에 보이지 않는다)
  - `firebase-admin` 등 새 의존성

## API·파일
- 새 경로: `POST /api/center/push-devices`, `POST /api/center/push-devices/remove`
- 바뀌는 동작(응답은 그대로): 채팅 WS의 센터 글, `PATCH /api/center/cases/{id}`, `POST /api/center/reset`(묶음도 지운다)
- 요청·응답 예시

  ```http
  POST /api/center/push-devices
  { "deviceToken": "fcm-token…", "platform": "android", "notice": "Có tin mới từ trung tâm",
    "cases": [{ "id": "C-251031-001", "token": "chat-token…" }, { "id": "C-0", "token": "wrong" }] }

  200 { "cases": ["C-251031-001"] }
  ```

- 새 파일: `app/push.py`, `tests/test_push.py`
- 수정: `app/routers/center.py`, `app/schemas.py`, `app/settings.py`, `app/store.py`, `app/store_sqlite.py`, `app/chat.py`, `app/main.py`(발송기 의존성), `tests/fakes.py`, `tests/test_store.py`, `README.md`, `CLAUDE.md`(결정 4)

## 완료 기준
- [x] `uv run ruff check . && uv run ruff format --check .` 통과
- [x] `uv run pytest` 통과(네트워크 없음). 메모리·SQLite 두 저장소에서:
  - [x] 맞는 채팅 토큰의 사례만 묶이고, 틀린 토큰·없는 사례는 오류 없이 빠진다. 21개·빈 목록·긴 `notice`·제어 문자는 422
  - [x] 센터가 채팅에 쓰면 묶인 기기 수만큼 가짜 발송기에 한 번씩 쌓이고, 근로자가 쓰면 쌓이지 않는다
  - [x] 상태를 바꾸면 보내고, 같은 상태로 다시 PATCH하면 보내지 않는다
  - [x] 60초 안의 두 번째 사건은 보내지 않고, 시계를 61초 옮기면 보낸다(`clock` 고정). 근로자가 채팅에 붙어 있으면 보내지 않는다
  - [x] 보낸 메시지의 제목·본문이 "for nav"·등록한 `notice`이고, `data`에 `kind`·`caseId` 외의 값이 없다(메시지 본문·상태가 없다)
  - [x] 발송기가 `UNREGISTERED`를 내면 그 토큰이 지워지고 다음 사건에는 보내지 않는다. 발송 실패·시간 초과에도 채팅·PATCH 응답은 그대로다
  - [x] `remove`·데모 초기화·30일 지난 묶음은 남지 않는다
  - [x] `WORKER_AUTH=google`에서 근로자 세션이 없으면 등록이 401, 센터 직원 쿠키로도 401
  - [x] `PUSH=off`(기본)이면 아무것도 보내지 않고, 등록 경로는 그대로 동작한다(앱 쪽 흐름을 서버 설정과 관계없이 확인할 수 있게)
  - [x] 로그(접근 로그·오류 로그)에 기기 토큰·채팅 토큰·`notice`·메시지 본문이 없다
- [ ] 실제 FCM 한 번(CI에서 돌지 않음): `PUSH=fcm`과 서비스 계정으로 띄운 서버 + app-front 07 Android 앱. 센터가 C-02에서 채팅에 쓰면 앱을 닫은 휴대폰에 근로자 언어의 알림 한 줄이 뜬다. 결과를 `## 결과`에 적는다

## 결과
- `uv run ruff check . && uv run ruff format --check .` → All checks passed, 92 files already formatted
- `uv run pytest` → 2968 passed(네트워크 없음. 시작 전 2873 → +95)
- 새 테스트
  - `tests/test_push.py` 82개(메모리·SQLite 두 저장소): 맞는 토큰만 묶기·다시 등록하면 갱신, 틀린 토큰만이면 빈 200, 422 경계 13가지(빈 목록·21개·81자·빈·공백·줄바꿈·`\x07`·`\x85`·`platform` 밖·빈 토큰·4097자·`null`), 경계값(20개·80자·4096자) 통과, `remove`(모든 사례에서 지움·없는 토큰 204), 데모 초기화, 30일 정리, 센터 글은 기기 수만큼·근로자 글은 0, 상태 변경은 보내고 같은 상태는 안 보냄, 60초 안 두 번째 건너뛰기·61초 뒤 보냄(`clock` 고정), 사례별 제한, 근로자 채팅 접속 중 건너뛰기, 메시지 모양(`for nav`·`notice`·`data`는 `kind`·`caseId`뿐), `UNREGISTERED` 토큰 삭제 후 다음 사건에 시도 안 함, 실패(`PushError`·임의 예외)·시간 초과에도 채팅·PATCH 응답 그대로, `PUSH=off`에서 등록은 되고 발송 작업 없음, 로그에 기기 토큰·채팅 토큰·`notice`·메시지 본문 없음, 설정(`PUSH` 값 검사, 값 누락·키 파일 없음·형식 오류는 경고 한 줄 후 `None`, 맞는 키면 `FcmSender`), `FcmSender`(테스트 생성 RSA 키의 서비스 계정 JSON + `httpx.MockTransport`: 토큰 교환 JWT의 서명·`iss`·`scope`·`aud`·`kid`, FCM 요청 주소·`Authorization`·본문 모양, 접근 토큰 만료 전 재사용·만료 60초 전 갱신, 오류 종류 `UNREGISTERED`·`INVALID_ARGUMENT`·`PERMISSION_DENIED`·`HTTP 500`·`HTTP 503`, 토큰 교환 실패 `token HTTP 400`, 네트워크 오류 `ConnectError`, 401 뒤 토큰 다시 받기)
  - `tests/test_store.py` 9개: 추가·갱신·해제, 30일 정리(조회·등록 때), 기기당 사례 20·사례당 기기 5 상한, 데모 초기화, SQLite 재시작 뒤 유지
  - `tests/test_worker_auth.py` 2개: `WORKER_AUTH=google`에서 세션 없으면 등록 401, 센터 직원 쿠키로도 401, 해제는 세션 없이 204
  - `tests/test_api.py` 2개: 등록 응답 형태·422, 해제 204
- 바뀐 API: 새 경로 `POST /api/center/push-devices`(`{ deviceToken, platform, notice, cases: [{ id, token }] }` → `{ cases: [...] }`), `POST /api/center/push-devices/remove`(`{ deviceToken }` → `204`). 기존 경로 응답은 그대로이고, 채팅 WS 센터 글·`PATCH /api/center/cases/{id}`(상태가 바뀔 때)·`POST /api/center/reset`(묶음 삭제)의 동작만 더했다
- 설정: `PUSH`(`off` 기본 | `fcm`), `FCM_PROJECT_ID`, `FCM_CREDENTIALS_FILE`. `fcm`인데 값이 빠졌거나 키를 못 읽으면 `push off: …` 경고 한 줄 뒤 발송기 없이 뜬다. `README.md`·`.env.example`·맥미니 배포 절차에 적었다
- 저장소: 표 `push_devices(case_id, device_token, platform, notice, updated_at, PRIMARY KEY(case_id, device_token))`. `add_push_device`·`push_devices(case_id, now)`·`remove_push_device`. 30일 정리는 등록·발송 조회 때 함께 한다
- 결정
  - 결정 1~5는 권장안(2026-10-31). 새 의존성 없음: 서비스 계정 JWT는 google-auth의 `crypt.RSASigner`·`jwt.encode`로 서명하고, 접근 토큰 교환과 FCM 발송은 `httpx`로 한다. google-auth 자격 증명의 `refresh()`는 동기 `requests` 전송이라 이벤트 루프를 막기 때문이다. 접근 토큰은 `expires_in`에서 60초 뺀 때까지 메모리에 두고, FCM이 401을 주면 버린다
  - **해제(`remove`)는 근로자 세션을 보지 않는다**(`WORKER_AUTH=google`이어도). 웹이 로그아웃 직후, 서버 세션이 이미 끝났을 때 부르고, 기기 토큰 자체가 열쇠다. 등록은 27과 같이 `require_worker`
  - 상한(기기당 사례 20, 사례당 기기 5)을 넘으면 거절하지 않고 가장 오래 갱신하지 않은 묶음을 지운다. 앱을 열 때마다 다시 등록하므로 쓰지 않는 기기·사례가 밀려난다
  - 60초 제한은 실제로 발송 작업을 띄운 사건부터 센다. 묶인 기기가 없거나 근로자가 채팅을 보고 있어 건너뛴 사건은 세지 않는다(근로자가 채팅을 닫은 뒤 첫 센터 글은 바로 간다). 메시지와 상태 변경은 같은 사례 제한을 나눈다
  - 발송 조율(`PushNotifier`: 60초 제한, 접속 확인, 백그라운드 작업, 시간 제한, 없는 토큰 지우기)도 `app/push.py`에 두고 `app.state.push`로 붙였다(LLM 호출 제한과 같이 프로세스 메모리). 라우터는 `_notify` 한 줄만 부른다. 채팅 방(`ChatHub`)은 연결마다 역할을 기억해 `has_worker`로 답한다
  - `PATCH /api/center/cases/{id}`를 `async def`로 바꿨다(발송 작업을 같은 이벤트 루프에 띄우려고). 응답은 그대로다
  - FCM 오류 종류는 `FcmError.errorCode` → `error.status` → `HTTP <상태>` 순으로 고르고, 대문자·`_`만인 값만 받아 응답 원문이 로그에 들어가지 않게 했다. `UNREGISTERED`·`INVALID_ARGUMENT`면 그 기기 토큰을 모든 사례에서 지운다
  - `notice`는 앞뒤 공백을 지운 뒤 1~80자, 유니코드 제어 문자(`Cc`, 줄바꿈·C1 포함)가 있으면 422
- 남은 것
  - [ ] 실제 FCM 한 번(`## 완료 기준` 마지막 항목): 아직 Firebase 프로젝트·서비스 계정이 없고 app-front 07 Android 앱도 없어 하지 못했다. `README.md` "근로자 앱 푸시 켜기" 절차로 키를 두고 확인한 뒤 여기에 적는다
  - iOS는 결정 5대로 APNs 키가 준비되면 같은 서버로 확인한다

## 메모
- 확인할 것(2026-10-31, app-front 07 검토): 근로자 웹은 센터 채팅 시트를 닫아도 숨기기만 해 채팅 WebSocket이 붙어 있다(frontend 39). Android에서 앱을 백그라운드로만 보낸 경우 WebView가 연결을 한동안 유지하면 "근로자가 채팅에 붙어 있음"으로 보여 알림을 건너뛸 수 있다. 실기기 확인(완료 기준 마지막 줄) 때 함께 보고, 그렇다면 "보고 있음"을 연결 유무가 아니라 웹이 보내는 보임 신호(채팅 `read`처럼)로 바꾸는 후속을 쓴다
- frontend 46 `## 메모`의 후속 둘 중 서버 몫이다. 앱 몫은 app-front 07(호스트)·08(웹 다리)이고, 근로자 화면에서 등록·해제·시트 열기를 하는 부분은 `@fe` 안이라 frontend 48로 따로 쓴다
- 기기 토큰을 사례 채팅 토큰으로 묶는 이유: 서버가 계정을 모르는 채로(27과 같은 열쇠로) "이 기기는 이 사례의 근로자"를 확인할 수 있다. 계정 바꾸기·공용 휴대폰은 웹이 `remove`를 부르고 호스트가 FCM 토큰을 지워(app-front 07 `pushUnregister`) 앞 계정의 알림이 오지 않게 한다
- 센터가 걸 때 알림(통화 착신)은 FCM 데이터 메시지 + 앱의 전체 화면 알림·CallKit이 필요해 범위가 크다. 이 항목이 끝난 뒤 backend·app-front 항목으로 따로 쓴다
- 프로세스 여러 개로 띄우면 60초 제한·접속 확인이 프로세스 메모리라 어긋난다. 지금은 `--workers 1`(채팅과 같다)
