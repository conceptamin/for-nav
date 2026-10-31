# 43. 근로자에게 센터 요청의 처리 상태와 새 메시지를 보여 주기

상태: 완료
의존: backend 26(`POST /api/center/my-cases`). 단독 모드 부분은 의존 없이 먼저 동작한다

## 목표
센터 회신(2026-10-31) 4항의 지원 절차 마지막 단계는 "상담 결과 및 후속 절차 안내, 추가 지원이 필요하면 후속 상담"이다. 지금 앱은 센터가 C-02에서 상태를 진행·완료로 바꾸거나 채팅에 답해도 근로자 화면에 아무 표시가 없다. `/my`에는 보낸 요청 id만 있고, 채팅 토큰이 세션(`umn.session`)에 있어 탭을 닫으면 그 요청의 채팅에 다시 붙을 수도 없다. 웹앱이라 푸시도 없으므로 근로자가 시트를 열어 두지 않으면 센터의 답을 놓친다. 앱을 다시 열었을 때 처리 상태와 읽지 않은 센터 메시지가 보이고, 그 대화로 바로 돌아갈 수 있게 한다.

## 범위
- 하는 것
  - **채팅 토큰을 계정별 기기 저장소로 옮긴다.** `SessionState.chatTokens` → `DeviceState.chatTokens`(`umn.device.<계정 키>`). 세션에 남은 옛 토큰은 처음 읽을 때 기기로 옮긴다. "내 데이터 지우기"가 함께 지운다. 이유: 며칠 뒤 돌아와도 같은 요청의 상태·채팅을 보려면 열쇠가 남아 있어야 한다. 같은 휴대폰의 다른 계정에는 보이지 않는다(기존 계정 분리 그대로)
  - **읽은 센터 메시지 수** `DeviceState.seenCenterMessages: Record<caseId, number>`. 근로자가 그 사례 채팅(시트 또는 S-12)을 열어 `history`를 받았을 때 센터가 보낸 메시지 수로 올린다
  - `domain/centerCase.ts`: `MyCaseView { id, status, centerMessages, lastCenterAt }` 타입
  - `src/api/center.ts`: `getMyCases(items: { id, token }[]) → MyCaseView[]`
    - API 모드: `POST /api/center/my-cases`(backend 26). 토큰이 맞지 않거나 사라진 사례는 응답에 없다
    - 단독 모드: 같은 브라우저의 `centerStore`에서 상태만 읽는다(`centerMessages: 0`, 채팅이 없다). 다른 탭의 센터 화면에서 상태를 바꾸면 근로자 화면에도 보인다
  - `useMyCases()` 구독: 로그인·프로필이 있고 보낸 요청이 있을 때, 화면이 보이는 동안(`document.visibilityState === 'visible'`) `MY_CASES_POLL_MS`(15초)마다 읽는다. 화면이 다시 보이면 곧바로 한 번 읽는다. 단독 모드는 `storage` 이벤트로 갱신한다
  - **하단 독 채팅 아이콘에 새 메시지 점**(SEED notification-badge Small): 읽지 않은 센터 메시지가 있는 사례가 하나라도 있으면 보인다. 아이콘의 `aria-label`에 "새 메시지"를 붙인다. 숫자는 쓰지 않는다(남용 금지)
  - **S-13 `/my` "센터로 보낸 요청"**: id만 있던 목록을 줄로 바꾼다. 줄마다 보낸 날, 상태 칩(`pill`: 접수됨 / 상담 중 / 완료), 읽지 않은 메시지가 있으면 "새 메시지" 칩. 줄을 누르면 그 사례로 센터 채팅 시트를 연다. 토큰이 없는 옛 요청(세션이 끝나 열쇠를 잃은 것)은 상태 없이 id만 보이고 누를 수 없다
  - **센터 채팅 시트**: 이어 보일 사례를 "토큰이 있는 가장 최근 요청"에서 "토큰이 있고 완료가 아닌 가장 최근 요청"으로 바꾼다. 머리 아래에 그 사례의 상태 칩. `/my`에서 고른 사례가 있으면 그 사례를 연다. 이어 볼 요청이 없으면(전부 완료) 지금처럼 새 요청 흐름이고, 위에 "지난 요청은 완료되었습니다" 한 줄
  - 실패: 상태를 읽지 못하면 마지막으로 받은 값을 그대로 두고, `/my` 목록 아래에만 `notice.info` 한 줄("상태를 불러오지 못했습니다"). 독의 점·시트는 조용히 마지막 값을 쓴다. 119 독은 영향이 없다
  - i18n 새 키 20개 언어: `caseStatus.new`, `caseStatus.progress`, `caseStatus.done`, `caseNewMsg`, `caseStatusFailed`, `casePrevDone`, `myCaseSent`(보낸 날 앞말). en·ko 직접, 나머지 기계 번역 초안(원어민 검수 필요)
  - `README.md`: 화면 구성 S-12·S-13 설명, "경로별 대체 정책" 표에 `POST /api/center/my-cases` 행, "비동기 UX 규칙" 시간 제한 목록에 15초 주기, "상태의 경계"(채팅 토큰·읽은 수가 기기 저장소로), "실서비스와 다른 점"(앱을 닫으면 알림 없음)
  - `design.md`: 독 채팅 아이콘의 새 메시지 점, `/my` 요청 줄, 시트 머리 아래 상태 칩
- 하지 않는 것
  - **앱이 닫혀 있을 때의 알림(푸시).** 웹앱만으로는 할 수 없다. Flutter 앱(`app/`)의 FCM 푸시 + 서버 발송은 따로 한다(메모)
  - 브라우저 `Notification` 권한 요청. Flutter WebView에서 동작하지 않고, 권한 팝업이 첫 경험을 막는다
  - 센터가 기록한 조치·결과(frontend 41의 `actions`·`referredTo`)를 근로자에게 보이기. 41이 끝난 뒤 이 화면에 한 줄을 더하는 후속으로 남긴다
  - 상태 열거값 변경, 센터 화면(C-01~C-03) 변경

## 화면·파일
- 화면: S-13 `/my`, 센터 채팅 시트(하단 독), 하단 독 채팅 아이콘. 경로 추가 없음
- API: `POST /api/center/my-cases`(backend 26)
- 수정: `src/domain/centerCase.ts`, `src/api/center.ts`, `src/components/centerLink.ts`(새), `src/state/AppState.tsx`, `src/components/WorkerLayout.tsx`, `src/components/CenterSheet.tsx`, `src/components/ChatPanel.tsx`(history를 받으면 읽은 수 올리기), `src/pages/worker/CenterRequest.tsx`(S-13 목록), `src/styles.css`, `src/i18n/*.ts`(20개), `README.md`, `design.md`
- `app-front/`가 `WorkerLayout`·`AppState`·`styles.css`를 공유하므로 `cd app-front && npm run build`도 돌린다

## 완료 기준
- [x] `npm run build` 통과, `cd app-front && npm run build` 통과
- [x] 단독 모드: 360px 근로자 탭에서 요청을 보내고, 1280px 다른 탭 `/center/cases/:id`에서 진행 → 완료로 바꾸면 근로자 `/my`의 칩이 접수됨 → 상담 중 → 완료로 바뀐다(새로고침 없이)
- [x] API 모드: 센터가 채팅에 답하면 15초 안에 근로자 독 채팅 아이콘에 점이 뜨고, 시트를 열어 대화를 보면 점이 사라진다
- [x] API 모드: 근로자 탭을 닫았다 다시 열어도(같은 계정) `/my`에 상태가 보이고 줄을 누르면 같은 대화가 열린다
- [x] 완료된 요청만 있으면 시트가 새 요청 흐름과 "지난 요청은 완료되었습니다"를 보인다
- [x] 서버를 끄면 `/my`에 "상태를 불러오지 못했습니다" 한 줄이 뜨고 마지막 칩은 그대로다. 119 독은 그대로 눌린다
- [x] 다른 계정으로 로그인하면 앞 계정의 요청·점이 보이지 않는다. "내 데이터 지우기" 뒤 토큰·읽은 수가 남지 않는다
- [x] en·vi·ko·ru·id 360px에서 `/my` 요청 줄과 시트 상태 칩이 넘치지 않는다. ar(RTL)에서 점과 칩 위치가 뒤집힌다

## 결과
- `npm run build` 통과, `cd app-front && npm run build` 통과
- 브라우저 확인(근로자 360px, 센터 1280px 다른 탭, 데모 로그인을 저장소에 심어 온보딩을 건너뜀)
  - API 모드(backend 26 브랜치 서버): 시트로 요청 전송 → 토큰·보낸 시각이 `umn.device.demo`에 들어가고 시트 요청 번호 줄에 "Received". 센터가 C-02에서 채팅 한 줄 + 진행 → 근로자 독 점이 약 3초 뒤(15초 주기 안) 뜨고 `aria-label`이 "Chat with the centre · New message". `/my` 줄: "C-65227 · Sent 31 October 2026", "In progress", "New message". 줄을 누르면 시트가 그 사례로 열려 센터 글이 보이고 점·칩이 사라진다(읽은 수 1)
  - 다시 열기: 세션을 비우고(새 탭과 같다) 옛 꼴로 세션에 토큰을 두고 다시 열면, 이 계정이 보낸 사례 토큰만 기기로 옮겨지고(남의 id 토큰은 버림) 세션에서 사라진다. `/my` 줄은 버튼이고 상태가 보인다
  - 센터가 완료 → `/my` 칩 "Completed", 독으로 연 시트는 "지난 요청은 완료" 한 줄 + 새 요청 흐름
  - 서버를 끄면 약 8초 뒤 `/my`에 "Couldn’t load the status…" 한 줄, 칩은 마지막 값, 119 링크 그대로
  - 서버를 다시 켜면(메모리 저장소라 사례가 사라짐) 그 사례 줄은 누를 수 없는 줄이 되고 시트는 새 요청을 묻는다
  - 언어: en·vi·ko·ru·id·my·ar에서 `/my` 줄과 칩이 360px 안(가로 넘침 없음). ar은 `dir=rtl`이고 칩이 오른쪽부터, 독 점이 말풍선의 왼쪽(끝 쪽). vi 시트의 요청 번호 줄 넘침 없음
  - 다른 계정(`other`)으로 바꾸면 요청 줄·점이 없다. "내 데이터 지우기" 뒤 `umn.device.demo`가 없고 세션에도 토큰이 없다
  - 단독 모드: `/api/` 요청 0건. 시트로 보낸 요청은 토큰 없이 저장되고, 센터 탭에서 진행 → 완료로 바꾸면 근로자 `/my` 칩이 새로고침 없이 따라 바뀐다. 줄은 누를 수 없다(토큰 없음)
- 동기화 기대값: `dump-fixtures`로 다시 만들어 보니 `generatedAt`만 달라 `parity.json`은 바꾸지 않았다(`domain/`에 더한 것은 타입과 `hasUnread`뿐이고 동기화 대상이 아니다)
- 결정
  - 읽은 수는 시트가 열려 있을 때(또는 S-12 화면에서 채팅이 보일 때)만 올린다. 시트는 닫아도 연결을 유지하므로, 닫힌 동안 온 글은 새 메시지로 남아야 한다
  - 상태를 한 번이라도 받은 뒤 응답에 없는 사례(데모 초기화·서버 재시작)는 이어 보지 않는다(`canResume`). 토큰을 기기에 오래 두게 되면서, 서버가 모르는 사례의 멈춘 채팅에 갇히는 것을 막으려고 확인 중에 더했다
  - 점 색은 SEED 기본 빨강이 아니라 `--brand-fg`(119와 헷갈리지 않게)
  - 시트·S-13이 같이 쓰는 상태 컨텍스트는 `components/centerLink.ts`에 따로 두었다(시트와 레이아웃이 서로 import하지 않게)
- 남은 문제: 앱이 닫혀 있을 때의 알림은 없다(메모의 후속). 새 문구 7개는 en·ko 외 기계 번역 초안이다

## 메모
- 센터 자문 검토 문서(`docs/center-advice-review.md`, 6장 A)의 첫 보완이다
- 저장 위치를 바꾸는 결정: 채팅 토큰은 그 사례 채팅·통화에 붙는 열쇠라 처음엔 세션에 두었다(backlog 25). 사후관리를 하려면 기기에 남아야 하므로 계정별 기기 저장소로 옮긴다. 공용 휴대폰 위험은 계정 분리와 "내 데이터 지우기"로 줄인다
- 앱이 닫혀 있을 때의 알림은 후속 둘: backend(상태 변경·센터 메시지 때 기기 토큰으로 FCM 발송, 기기 토큰 등록 경로)와 app(FCM 등록, 알림을 누르면 시트를 연 채 앱 열기). 이 항목이 끝난 뒤 각 영역 backlog로 쓴다
- 새 문구는 기계 번역 초안이다. 원어민 검수 순서는 README "확인이 필요한 값"을 따른다
