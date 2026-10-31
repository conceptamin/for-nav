# 41. 센터 사례에 상담 분야와 조치 기록을 두기

상태: 대기
의존: 없음(backend 24가 같은 필드를 받는다. 프론트가 원본이므로 이 항목을 먼저 한다)

## 목표
센터 회신(2026-10-31): 센터는 의료 상담을 **의료·보건 / 건강보험·공공의료 / 의료비 지원** 세 분야로 집계하고, 접수 → 정보 제공 → 통역·관계기관 연계 → 결과 안내·사후관리 순서로 지원하며, 세부 유형별 건수는 따로 집계하지 않는다. 앱의 센터 사례(`CenterCase`)에는 근로자가 고른 요청 종류(`requestTypes`)와 신규/진행/완료 상태만 있어 센터의 분류·절차와 맞지 않고, 센터가 실적 집계에 쓸 수 없다. 사례에 분야와 조치 기록을 더해 센터 보고 형식과 맞춘다. 통계 화면(C-03)에 보이는 것은 42다.

## 범위
- 하는 것
  - `domain/centerCase.ts`
    - `CaseCategory = 'medical' | 'insurance' | 'cost'`(의료·보건 / 건강보험·공공의료 / 의료비 지원), `CATEGORY_KO`
    - `CenterCase.category: CaseCategory`. 접수 때 결정적 규칙 `defaultCategory({ coveragePath, requestTypes })`로 채운다: `coveragePath === 'ulsanSupport'` → `cost`, 그 밖에 `coveragePath === 'nhis'`이거나 `requestTypes`가 `['policy']`뿐이면 `insurance`, 나머지 `medical`. 직원이 C-02에서 바꿀 수 있다
    - `CaseAction = 'info' | 'interpret' | 'referral' | 'followUp'`(정보 제공 / 통역 지원 / 관계기관 연계 / 후속 상담 필요), `CenterCase.actions: CaseAction[]`(처음 `[]`)
    - `ReferralTarget = 'nhis' | 'kcomwel' | 'hospital' | 'ulsan' | 'other'`, `CenterCase.referredTo: ReferralTarget[]`(처음 `[]`). `referral`을 켤 때만 보인다
  - C-02 `/center/cases/:id`: "상태 변경" 아래 "분야"(단일 선택)와 "조치"(체크, 연계면 기관 체크) 칸. 저장 실패는 기존 상태 변경과 같은 실패 문구 + 다시 시도
  - C-01 `/center`: 분야 필터 칩(전체/셋), 목록에 분야 열
  - `src/api/center.ts`: `setCaseStatus(id, status)`를 `updateCase(id, patch)`로 일반화. `patch`는 `status`·`category`·`actions`·`referredTo` 중 있는 것만 보낸다. API 모드는 `PATCH /api/center/cases/{id}` 본문이 그 모양이다. 단독 모드는 `centerStore`가 같은 patch를 합친다
  - `state/centerStore.ts`: 옛 저장 사례(세 필드 없음)를 읽을 때 `category`는 규칙으로, `actions`·`referredTo`는 `[]`로 채운다(37의 `requestType` → `requestTypes` 처리와 같은 자리)
  - `data/mock.ts`: mock 24건의 `category`는 규칙으로 계산한다(새 난수를 뽑지 않아 시드 순서가 그대로다). `actions`·`referredTo`는 `[]`
  - `scripts/dump-fixtures.ts`에 `defaultCategory` 입력·출력을 더하고 `parity.json`을 다시 만든다
  - `README.md` "상태의 경계"·C-01~C-02 설명
- 하지 않는 것
  - 상태 열거값(`new`/`progress`/`done`) 변경. 센터 절차 4단계를 상태로 바꾸는 안은 접었다(메모)
  - 자유 입력 메모 칸. 상담 경위에 개인정보가 들어가므로 열거값만 둔다
  - C-03 통계(42), `backend/` 코드(backend 24)

## 화면·파일
- 화면: C-01 `/center`, C-02 `/center/cases/:id`. 경로 변경 없음
- 수정: `src/domain/centerCase.ts`, `src/pages/center/Center.tsx`, `src/api/center.ts`, `src/state/centerStore.ts`, `src/data/mock.ts`, `scripts/dump-fixtures.ts`, `backend/tests/fixtures/parity.json`(재생성), `README.md`
- API: `PATCH /api/center/cases/{id}` 본문 `{ status }` → `{ status?, category?, actions?, referredTo? }`. `CenterCase` 응답에 `category`·`actions`·`referredTo` 추가. 센터 화면 문구는 한국어 고정이라 i18n 키 없음

## 완료 기준
- [ ] `npm run build` 통과
- [ ] 단독 모드 1280px `/center`: 분야 필터로 목록이 걸러지고, 상세에서 분야를 바꾸면 목록이 따라 바뀐다. 조치 체크가 새로고침 뒤에도 남는다
- [ ] 360px에서 울산 지원 경로로 보낸 사례의 기본 분야가 의료비 지원, 제도 상담만 고른 사례가 건강보험·공공의료, 그 밖이 의료·보건이다
- [ ] `parity.json` 재생성 → `defaultCategory` 항목 추가와 `generatedAt`만 바뀐다
- [ ] 세 필드가 없는 옛 꼴 사례를 localStorage에 넣어도 목록·상세가 열린다

## 결과

## 메모
- API 계약이 바뀐다(`PATCH` 본문 확장, `CenterCase` 응답 3필드). 서버가 맞추기 전(backend 24)에는 API 모드에서 분야·조치 저장이 서버에 남지 않고, `GET`에 필드가 없으면 프론트가 기본값으로 채운다. 상태 변경은 그대로 동작한다
- 센터 절차 4단계를 `status`로 바꾸는 안은 접었다: 상태 열거값은 mock·parity·백엔드·통계 원천에 두루 쓰여 바꾸면 모두 깨지고, 한 사례에 정보 제공과 통역 지원이 겹치므로 체크 목록이 더 맞다
- 분야 기본값 규칙은 `coverage.ts`의 경로와 요청 종류만 본다. 증상 입력 내용으로 분야를 가르지 않는다(판단을 넣지 않는다)
- 센터가 "세부 유형별 건수는 별도 집계하지 않는다"고 했으므로, 이 필드가 쌓이면 42의 통계가 그 집계를 대신할 수 있다. 센터에 제안할 거리다
