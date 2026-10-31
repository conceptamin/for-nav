# 34. 한 계정에 프로필 여러 개 + 생년월일 칸을 앱 언어로

상태: 완료
의존: 28 (근로자 Google 로그인, 계정별 기기 저장소), 12 (홈·내 정보)

## 목표
2026-10-31 사용자 요청: "프로필을 여러 개 추가 가능하도록 추가 버튼 생성해줘. 한 계정으로 여러 개 추가 가능하게. 그리고 간단 프로필 만들 때 '연도-월-일'이 언어에 맞게 변환되지 않아. 그 부분 수정해."
한 계정(같은 Google 계정·데모 계정) 안에 프로필을 여러 개 두고 골라 쓰게 한다. 간단 프로필의 생년월일 칸이 앱 언어를 따르게 한다.

## 범위
- 하는 것
  - `AppState`: 계정별 기기 저장소의 `profile` 하나를 `profiles: { id, profile }[]` + `activeProfileId`로 바꾼다. `profile`(지금 프로필)은 그대로 내보내 리포트·센터 요청·홈 나 줄이 손대지 않고 지금 프로필을 쓴다. `addProfile`·`selectProfile`·`deleteProfile`을 더한다. 옛 저장값(`profile` 하나)은 처음 읽을 때 첫 프로필로 옮긴다
  - S-13 `/my` 프로필 카드: `프로필 수정` 아래에 다른 프로필 목록(누르면 바뀜) → `＋ 프로필 추가`(→ `/signup?next=/my&new=1`) → 프로필이 둘 이상이면 `이 프로필 삭제`(확인 창). 생년월일 줄을 그 언어의 날짜로
  - S-03 프로필 단계: `?new=1`이면 빈 칸으로 열고 제목이 `프로필 추가`, 저장하면 프로필을 하나 더 만들고 그것으로 바꾼다
  - 생년월일 입력: `input[type=date]` 대신 연·월·일 `select` 셋(`BirthDateInput`). 순서는 언어별 표(`DATE_ORDER`), 달 이름은 Intl. 브라우저가 그 언어 자료를 모르면 숫자
  - 새 문구 7개(`dateYear`·`dateMonth`·`dateDay`, `profileAdd`·`profileOthers`·`profileDelete`·`profileDeleteConfirm`)를 20개 언어에
- 하지 않는 것
  - 프로필 이름·별명(이름을 받지 않는다는 원칙 그대로. 성별·생년월일로 구별해 보인다)
  - 리포트·센터 사례 id를 프로필별로 나누기(계정에 묶인다. 리포트에는 만들 때의 프로필 기본 정보가 이미 들어 있다)
  - 서버 저장·동기화(프로필은 계속 기기에만 있다)

## 화면·파일
- 화면: S-03 `/signup`(프로필 단계, `?new=1`), S-13 `/my`. 경로 추가 없음(쿼리만)
- 파일: `src/state/AppState.tsx`, `src/components/common.tsx`(`BirthDateInput`), `src/i18n/index.ts`(`DATE_ORDER`·`dateFormat`·`hasDateLocale`·`formatIsoDate`), `src/i18n/*.ts` 20개, `src/pages/worker/Onboarding.tsx`, `src/pages/worker/CenterRequest.tsx`, `src/styles.css`(`.date-parts`), `design.md`, `README.md`
- `app-front/`는 `AppState`·근로자 화면을 공유하므로 빌드로 확인한다

## 완료 기준
- [x] `npm run build` 통과, `cd app-front && npm run build` 통과
- [x] vi 간단 프로필의 생년월일 칸이 `Ngày · Tháng · Năm` 순서, ko는 `1988년 · 7월 · 15일`, en은 `Day · Month · Year`
- [x] `/my`에서 `프로필 추가` → 빈 칸 → 저장하면 `/my`로 돌아와 새 프로필이 지금 프로필이고 앞 프로필이 "다른 프로필"에 있다. 누르면 바뀌고 홈 나 줄도 바뀐다
- [x] 프로필이 둘일 때 지우면 하나가 남아 지금 프로필이 되고 삭제 버튼이 사라진다
- [x] 옛 저장값(`profile` 하나)이 첫 프로필로 옮겨지고 `profile` 키가 남지 않는다
- [x] 360px에서 가로 스크롤 없음(ar RTL 포함)

## 결과
- `cd frontend && npm run build` → 통과, `cd app-front && npm run build` → 통과(둘 다 기존 500kB 청크 경고만)
- 브라우저(dev 서버 5181, 360px, 데모 계정)
  - vi `/signup`: `Ngày · Tháng · Năm`, 28 / Tháng 2 / 1990 + Nam 저장 → `/my` 생년월일 `28 tháng 2, 1990`
  - vi `/my` → `＋ Thêm hồ sơ` → 빈 칸 → 3 / Tháng 11 / 1995 + Nữ 저장 → 지금 프로필 `3 tháng 11, 1995`, 다른 프로필 `👤 Nam · 28 tháng 2, 1990`. 누르면 바뀌고 `/home` 나 줄 `Nam · 1990`
  - ko 옛 저장값(`profile` 하나) → `profiles` 1개 + `activeProfileId`, `profile` 키 없음. 칸 `1988년 · 7월 · 15일`
  - ar: `اليوم · الشهر · السنة`(오른쪽부터), `scrollWidth` 360. tl: `Buwan · Araw · Taon`(Hulyo). en `/signup?new=1`: 제목 `Add profile`, `Day · Month · Year`
  - ne: 이 브라우저(Electron)에는 ne·mn·my·si·km·ky 날짜 자료가 없어 Intl이 한국어(`1990년 9월`)로, uz·kk는 `M09`로 그렸다 → 숫자(`1988 · 7 · 15`) + 문구 표의 자리 이름(`वर्ष · महिना · गते`)으로 대체됨을 확인
  - en `/my`: 프로필 둘에서 `Delete this profile` → 하나 남고 지금 프로필, 삭제 버튼 사라짐
  - 콘솔 오류 없음
- 결정
  - 날짜 칸을 직접 그렸다. `input[type=date]`의 자리표시(`연도-월-일`)와 달력은 페이지 `lang`이 아니라 휴대폰·브라우저 언어를 따라 앱에서 바꿀 수 없다
  - 순서는 Intl에서 읽지 않고 표로 정했다. 날짜 자료가 줄어든 브라우저는 모르는 언어를 기본 언어 순서로 그려서다(표는 Intl이 아는 en·vi·ko·ru·ar·ja·zh·th·fr·tl·id 결과와 같다)
  - 그레고리력으로 고정했다. 태국어 Intl 기본은 불기(2533)라 홈 나 줄의 서기 연도와 어긋난다
  - 프로필에 이름을 받지 않고 성별·생년월일로 구별한다. 성별·생년월일이 같은 두 프로필은 구별되지 않지만 이름을 받지 않는 원칙이 앞선다
  - 마지막 프로필은 지울 수 없다. 프로필 없이 홈에 머무는 길을 만들지 않는다(전체 삭제는 `/my` 맨 아래 그대로)

## 메모
- 새 문구 7개는 en·ko를 뺀 18개 언어가 기계 번역 초안이다. 원어민 검수가 필요하다(backlog 16과 같은 상태)
