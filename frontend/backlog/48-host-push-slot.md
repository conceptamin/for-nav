# 48. 앱 호스트 푸시 자리: 기기 등록·해제와 알림으로 시트 열기

상태: 완료(실제 앱 알림은 app-front 07·08에서 확인)
의존: 46(`DeviceState.chatTokens`, `useCenterLink().openCase`), backend 28(`POST /api/center/push-devices`, `…/remove`). 다리·호스트는 app-front 07·08

## 목표
센터가 채팅에 답하거나 요청 상태를 바꿔도 앱이 닫혀 있으면 근로자는 알 수 없다(frontend 46 `## 메모`). app-front 07·08이 Flutter 호스트의 FCM 기기 토큰과 "알림을 눌러 열었다"를 다리로 이어 오는데, 서버 등록에 필요한 채팅 토큰·API 모드와 시트를 여는 `openCase`는 모두 `@fe` 안에 있다. 이 항목은 앱이 호스트 푸시를 등록할 자리(`setHostPush`)를 두고, 근로자 화면이 그 자리로 기기를 이 계정의 사례에 묶고·풀고, 알림으로 열린 사례의 시트를 연다. backlog 35(`setNativeGoogleSignIn`)·37(`setHostSpeech`)과 같은 모양이다.

## 결정이 필요한 것
1. **등록과 시트 열기를 어디서 하나.** app-front 08 결정 1의 권장안대로 이 폴더(`api/push.ts` + `WorkerLayout`)에서 한다. 앱은 다리 함수만 등록한다.
   - 결정(2026-10-31): 권장안. 사용자가 #164의 backlog 셋을 "구현하자"고 했다. app-front 08이 이 항목을 "frontend 47(가칭)"으로 불렀으나 47은 메신저 읽음 표시가 써서 48로 쓴다.
2. **해제 시점을 어떻게 아나.** `AppState`에 해제 신호를 더하지 않고, `WorkerLayout`이 계정 키가 바뀌는 것(로그아웃·내 데이터 지우기·계정 바꾸기·서버 세션 끝)을 보고 앞 계정의 기기를 푼다. 로그아웃 버튼이 있는 S-13은 `WorkerLayout` 안이다.
   - 결정(2026-10-31): 위대로. `AppState`의 액션마다 신호를 끼우면 같은 일을 네 곳에 적게 된다. 서버 세션이 끝나 계정이 비는 경우도 풀리지만, 다시 로그인하면 곧바로 다시 묶인다.
3. **`notice`(알림 본문) 문구.** backend 28 결정 2대로 근로자 언어의 한 문장(`pushNotice`)을 등록 때 보낸다. 화면에는 보이지 않는다. 메시지 내용·상태 이름·사례 번호·의료 낱말을 넣지 않는다.
   - 결정(2026-10-31): 권장안. ko "센터에서 새 소식이 있습니다", en "New update from the centre"

## 범위
- 하는 것
  - `src/api/push.ts`(새)
    - `HostPush = { platform; getToken(): Promise<string | null>; onToken(cb); unregister(); onOpen(cb) }`, `setHostPush(push | null)`. 호스트의 `init`은 첫 화면보다 늦게 오므로 화면은 자리를 구독해서 읽는다(`useSyncExternalStore`)
    - `usePushDevice(account, refs, notice)`: API 모드이고 자리가 있고 채팅 토큰이 있는 사례가 있으면 `getToken()` → `POST /api/center/push-devices`(`cases` 최대 20개). 같은 계정·문구·사례면 다시 보내지 않고, 사례 목록·언어·토큰이 바뀌면 다시 보낸다. 페이지마다(앱을 열 때마다) 한 번은 보낸다. 권한 거부(`null`)면 이 페이지에서는 다시 묻지 않는다. 실패는 다시 시도하지 않는다(`logFailure` 한 줄, 화면 문구 없음)
    - 계정이 바뀌거나 비면 `POST /api/center/push-devices/remove` → `unregister()` 순서. 서버가 실패해도 토큰은 지운다(FCM이 거절하면 서버가 지운다, backend 28). 해제 전에 시작한 등록은 끝나도 보내지 않는다
    - `usePushOpen(cb)`: 알림으로 열린 사례 id
    - 기기 토큰은 이 파일의 메모리에만 둔다. 저장소·`console`에 남기지 않는다
  - `src/components/WorkerLayout.tsx`: `usePushDevice(app.account, refs, t('pushNotice'))`(`refs`는 frontend 46의 내 요청 목록 그대로), `usePushOpen`: 로그인하고 프로필까지 있고(`app.ready`) 이 계정의 `chatTokens`에 있는 사례면 `openCase`, 아니면 무시
  - `src/i18n/*.ts`: `pushNotice` 20개 언어
  - `README.md`: 폴더 구조의 `api/` 줄, "경로별 대체 정책" 표에 푸시 등록 줄, "상태의 경계"에 기기 토큰. `CLAUDE.md` "백엔드·모델링과의 경계"의 공유 import 목록
- 하지 않는 것
  - 다리·호스트 코드(app-front 07·08). 이 폴더는 다리를 모른다
  - 브라우저 웹 푸시·`Notification` 권한(app-front 08 결정 4). 단독 웹앱은 지금처럼 15초 주기로 읽는다
  - 화면·문구 변화. 알림 권한 설명 화면도 두지 않는다(app-front 07 결정 4)
  - `AppState` 변경(결정 2)

## 화면·파일
- 화면: 바뀌는 화면 없음. 앱 안에서 알림으로 열면 센터 채팅 시트(frontend 46)가 그 사례로 열린다
- API: `POST /api/center/push-devices`, `POST /api/center/push-devices/remove`(backend 28)
- 파일: `src/api/push.ts`(새), `src/components/WorkerLayout.tsx`, `src/i18n/*.ts`(20개), `README.md`, `CLAUDE.md`
- 새 문구 키: `pushNotice`

## 완료 기준
- [x] `cd frontend && npm run build` 통과, `cd app-front && npm run build` 통과
- [x] 브라우저(자리 없음), 단독·API 모드: 센터 요청을 보내도 `/api/center/push-devices` 요청이 없다. 화면은 지금과 같다
- [x] 가짜 자리를 등록한 브라우저(API 모드): 토큰 있는 사례가 있으면 등록이 한 번 나가고, 언어를 바꾸면 새 `notice`로 한 번 더, 로그아웃하면 `remove` → `unregister` 순서다
- [x] `onOpen`이 이 계정의 사례면 시트가 그 사례로 열리고, 모르는 사례면 아무것도 열지 않는다
- [x] `localStorage`·`sessionStorage`·`console`에 기기 토큰이 없다

## 결과
- `cd frontend && npm run build` → 통과, `cd app-front && npm run build` → 통과
- 브라우저 확인(Playwright 헤드리스 Chromium, 360px, 데모 계정에 채팅 토큰 있는 사례 둘을 넣은 저장소). 서버 경로는 가로채서 흉내 냈다(backend 28은 따로 구현 중). 가짜 자리는 개발 서버에서 `setHostPush`를 직접 불러 등록했다
  - API 모드·자리 없음, 단독 모드·자리 없음, 단독 모드·자리 있음: `/api/center/push-devices` 요청 0건
  - API 모드·자리 있음(en): 등록 1건, 본문 `platform: android`, `notice: New update from the centre`, `cases` 둘(채팅 토큰 포함). 다른 화면으로 옮겨도 다시 보내지 않는다
  - 언어를 vi로 바꾸면 `notice: Có tin mới từ trung tâm`으로 한 번 더, 토큰 갱신(`onToken`)이면 새 토큰으로 한 번 더
  - `onOpen('C-999999-999')`(모르는 사례): 시트가 열리지 않는다. `onOpen('C-251031-002')`: 센터 채팅 시트가 그 사례로 열린다
  - S-13 로그아웃: `POST /api/center/push-devices/remove`(지금 토큰) → `unregister()` 순서
  - `localStorage`·`sessionStorage`·`console`에 기기 토큰 없음
- 실제 앱(FCM 토큰·알림 탭)은 app-front 07·08에서 확인한다
- 고친 것(2026-10-31, app-front 07 실기기 확인 중 발견): 앱을 완전히 껐다 켜면 세션의 언어가 사라져 S-01부터 시작하는데, 계정·프로필은 남아 있어 그때 영어 `pushNotice`로 다시 등록해 서버의 근로자 언어 문장을 덮어썼다(에뮬레이터에서 다음 알림이 "New update from the centre"로 옴). 언어를 고르기 전에는 등록하지 않게 했다(`notice`가 `null`이면 보내지 않음). Playwright로 언어 없는 세션에서 등록 0건 확인

## 메모
- app-front 08이 "frontend 47(가칭)"으로 부른 항목이다
- `pushNotice`는 en·ko만 직접 썼고 나머지 18개 언어는 기계 번역 초안이다(backlog 16). vi(`Có tin mới từ trung tâm`)를 비롯해 원어민 검수가 필요하다. 잠금 화면에 뜨므로 짧고 내용이 없어야 한다
