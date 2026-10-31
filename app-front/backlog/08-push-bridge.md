# 08. 앱 푸시 알림: 웹 다리로 기기 토큰 받기와 알림으로 시트 열기

상태: 대기
의존: 07(같은 PR, 07 결정 1), backend 28(`POST /api/center/push-devices`), frontend 46(`DeviceState.chatTokens`, `useCenterLink().openCase`), frontend 47(가칭, 결정 1의 근로자 화면 자리)

## 목표
07의 호스트가 FCM 기기 토큰과 "알림을 눌러 열었다"를 다리로 알려 주면, 웹이 그 토큰을 이 계정의 사례 채팅 토큰과 함께 서버에 등록하고(backend 28), 알림으로 열렸을 때 센터 채팅 시트를 그 사례로 연다(frontend 46 `openCase`). 이 문서는 `src/bridge/`와 `src/main.tsx`의 연결이고, 등록·해제·시트 열기를 실제로 하는 근로자 화면 쪽은 `@fe` 안이라 frontend 항목으로 따로 한다(06 → frontend 35와 같은 모양).

## 결정이 필요한 것
권장안으로 적었다. 사용자 확인 뒤 결과와 날짜를 남긴다.

1. **등록과 시트 열기를 어디서 하나.** 서버 등록에는 이 계정의 채팅 토큰(`DeviceState.chatTokens`, `AppState`)과 API 모드·시간 제한(`frontend/src/api/`)이 필요하고, 시트 열기는 `WorkerLayout`이 주는 `CenterLinkContext`의 `openCase`다. 셋 다 `@fe` 안이다.
   - 권장: **frontend에 "호스트 푸시 자리"를 두는 항목(frontend 47, 가칭)을 쓰고, 이 앱은 다리 함수만 등록한다.** `setHostSpeech`(frontend 37)·`setNativeGoogleSignIn`(frontend 35)과 같은 모양이다
     - `frontend/src/api/push.ts`: `setHostPush(push: HostPush | null)`. `HostPush = { getToken(): Promise<string | null>; onToken(cb): () => void; unregister(): void; onOpen(cb: (caseId) => void): () => void }`
     - `WorkerLayout`(채팅 토큰·`openCase`·`feed`가 이미 모인 곳): API 모드이고 등록된 자리가 있고 이 계정에 토큰 있는 사례가 있으면 `getToken()` → `POST /api/center/push-devices`(`cases`는 토큰 있는 사례 최대 20개, `notice`는 새 i18n 키 `pushNotice`의 현재 언어 문장). 새 요청을 보냈을 때·언어를 바꿨을 때·토큰이 바뀌었을 때 다시 등록한다. 로그아웃·계정 바꾸기·"내 데이터 지우기" 때 `POST /api/center/push-devices/remove` 뒤 `unregister()`
     - `onOpen(caseId)`: 이 계정의 `chatTokens`에 있는 사례면 `openCase(caseId)`(frontend 46). 없으면 무시한다(다른 계정의 알림, 지운 사례). 진입 순서 가드를 다 지나지 않았으면(로그인 전 등) 무시한다
     - 단독 모드·호스트 없음에서는 자리가 비어 아무것도 하지 않는다. 화면·문구 변화 없음(새 i18n 키는 서버로 보내는 알림 문장일 뿐 화면에 보이지 않는다)
   - 대안: 이 앱이 `WorkerLayout` 아래에 레이아웃 경로를 하나 끼워 `useCenterLink()`·`useApp()`을 직접 부르고, 등록 요청도 이 앱에서 보낸다. `frontend/`를 고치지 않지만 API 모드·시간 제한·실패 정책을 이 앱에서 다시 정하게 되고(`CLAUDE.md` "frontend의 정책을 다시 정하지 않는다"), `WorkerLayout` 안쪽 구조에 기대어 frontend 변경에 쉽게 깨진다
2. **`pushOpen`이 근로자 화면보다 먼저 오면.** 호스트는 `init` 바로 뒤에 보내는데(07), 그때 frontend 쪽 구독(`onOpen`)이 아직 없을 수 있다.
   - 권장: 다리가 **마지막 `pushOpen` 하나를 들고 있다가** 첫 구독자에게 넘기고 비운다. 오래된 것을 늦게 여는 일이 없게 30초가 지나면 버린다
3. **등록을 얼마나 자주 보내나.**
   - 권장: 페이지마다(앱을 열 때마다) 한 번, 그 뒤에는 보낼 사례 목록·언어·토큰이 바뀔 때만. 실패하면 다시 시도하지 않고 다음 변경·다음 실행 때 보낸다(조용히 실패, `/my`에도 문구 없음). 서버의 30일 정리(backend 28 결정 4)는 앱을 열 때마다 하는 등록으로 갱신된다
4. **단독 웹앱(`www.for-nav.com`, `frontend/`)과 호스트 없는 브라우저.**
   - 권장: **웹 푸시(Service Worker + VAPID)는 하지 않는다.** 브라우저 `Notification` 권한은 frontend 46에서 하지 않기로 했고, iOS Safari 웹 푸시는 홈 화면에 추가한 웹앱에서만 된다. 단독 웹앱은 frontend 46대로 다시 열 때 15초 주기로 읽는다. README "실서비스와 다른 점"에 "알림은 앱에서만"을 적는다
   - 이것은 `CLAUDE.md`의 "호스트가 없어도 똑같이 동작한다"의 예외가 아니다. 호스트 없음에서는 지금 동작 그대로이고, 앱에서 알림이 더해질 뿐 화면·문구는 같다

## 범위
- 하는 것
  - **다리(`src/bridge/host.ts`)**
    - `FEATURE_PUSH = 'push'`
    - `requestPushToken(): Promise<string | null>`: `pushRegister`를 보내고 `pushToken` 하나를 기다린다. `error: denied`는 `null`(권한 거부는 실패가 아니다), `failed`는 예외. 앞 요청이 끝나기 전에 또 부르면 같은 약속을 돌려준다
    - `listenPushToken(cb): () => void`: 요청 없이 온 `pushToken { token }`(토큰 갱신)
    - `unregisterPush()`: `pushUnregister`를 보낸다
    - `listenPushOpen(cb): () => void`: `pushOpen.caseId`. 결정 2의 보관(마지막 하나, 30초)
    - 토큰·`caseId`는 함수 반환값·콜백으로만 지나가고 저장하지 않는다. `console`에 찍지 않는다(오류는 `type`만)
  - **`src/main.tsx`**: 호스트 상태를 구독해 `present && features.includes('push')`일 때만 `setHostPush({...})`(frontend 47), 아니면 `null`. 06·04의 등록과 같은 자리·모양
  - **`src/pages/HostCheck.tsx`(`/__host`)**: features 줄에 `push`가 보이고, 개발용 "푸시 시험" 버튼 → `requestPushToken()` 결과 종류(`token 받음` / `거부` / `실패`)만 보인다(토큰 값은 보이지 않는다). 마지막 `pushOpen`을 받았는지(예/아니오)
  - `README.md` 계약 부분은 07이 고친다(같은 PR). 이 문서 몫은 "상태의 경계"(FCM 토큰은 메모리에만), "실서비스와 다른 점"(알림은 앱에서만)
- 하지 않는 것
  - `@fe` 안의 파일 수정(등록·해제·시트 열기·`pushNotice` 문구는 frontend 47)
  - 브라우저 웹 푸시, `Notification` 권한(결정 4)
  - 앱이 앞에 있을 때 알림을 받아 곧바로 다시 읽기(07 결정 5)
  - 알림 문구를 이 앱에 두기

## 화면·계약·파일
- 화면: 근로자 화면 변화 없음. 알림을 눌러 열면 센터 채팅 시트가 그 사례로 열린 채 시작한다(시트는 frontend 46 그대로). `/__host`에 푸시 줄과 시험 버튼
- 계약: 07의 `pushRegister`·`pushUnregister`·`pushToken`·`pushOpen`, `init.features`의 `push`. 이 문서는 웹 쪽 처리만 정한다
- 수정: `src/bridge/host.ts`, `src/bridge/HostProvider.tsx`(필요하면), `src/main.tsx`, `src/pages/HostCheck.tsx`, `README.md`("상태의 경계", "실서비스와 다른 점")
- frontend 47(가칭) 몫: `frontend/src/api/push.ts`(새), `frontend/src/api/center.ts`(`registerPushDevice`, `removePushDevice`), `frontend/src/components/WorkerLayout.tsx`, `frontend/src/state/AppState.tsx`(로그아웃·계정 바꾸기·지우기 때 해제 신호), `frontend/src/i18n/*.ts`(`pushNotice` 20개 언어, en·ko 직접, 나머지 기계 번역 초안), `frontend/README.md`·`frontend/CLAUDE.md` "경계"(이 앱이 import하는 `@fe/api/push`)

## 완료 기준
- [ ] `cd app-front && npm run build` 통과, `cd frontend && npm run build` 통과
- [ ] 브라우저(호스트 없음): `/__host`의 features에 `push`가 없고 "푸시 시험"이 `호스트 없음`이다. 근로자 화면에서 센터 요청을 보내도 `/api/center/push-devices` 요청이 없다
- [ ] 단독 모드(앱 안이어도): 등록 요청이 없다
- [ ] 07의 Android 앱(API 모드, `PUSH=off` 서버로도 된다): 센터 요청을 보내면 `pushRegister` → `pushToken` → `POST /api/center/push-devices`가 한 번 나가고 응답의 `cases`에 그 사례가 있다. 앱을 다시 열면 한 번 더 나간다. 언어를 바꾸면 새 `notice`로 다시 나간다
- [ ] 알림으로 앱을 열면(백그라운드·꺼진 상태 모두) 시트가 그 사례로 열린다. 다른 계정으로 로그인한 상태에서 받은 `pushOpen`(시험 버튼으로 흉내)은 아무것도 열지 않는다
- [ ] 로그아웃하면 `POST /api/center/push-devices/remove` → `pushUnregister` 순서로 나간다
- [ ] 웹 `console`, `localStorage`, `sessionStorage`에 FCM 토큰이 없다

## 결과
(구현 후 작성)

## 메모
- frontend 46 `## 메모`의 앱 몫 중 웹 다리 쪽이다. 호스트는 07, 서버는 backend 28
- frontend 47(가칭)은 이 문서와 07·backend 28이 확인되면 `frontend/backlog/`에 쓴다. 번호는 그때 main의 최신 번호를 다시 본다
