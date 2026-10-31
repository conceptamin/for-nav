# 56. 사진을 의사에게 보여 줄 메모에 붙이기

상태: 완료
의존: 10

## 목표
S-05에서 사진을 올릴 수 있는데 어디에도 남지 않고 버려져서, 올린 의미가 없었다. 사진을 의사에게 보여 줄 메모(S-11)에만 붙여 진료 때 함께 보이게 한다. 서버로는 여전히 보내지 않는다(사용자 결정, 2026-10-31).

## 범위
- 하는 것
  - `PhotoPicker`가 고른 사진을 긴 변 960px·JPEG 품질 0.6 data URL로 줄인다(object URL·`usePhotoCleanup` 삭제)
  - 증상 입력을 마치면 사진을 세션(`umn.session.photos`)에 둔다. `Intake`에는 넣지 않는다
  - S-11 항목 고르기에 `사진 (n)` 체크(기본 켜짐)를 둔다. 켜져 있으면 만든 리포트에 이 기기에서 `photos`를 붙인다
  - S-11 리포트 보기(한국어·모국어 모두)에 `사진` 줄과 썸네일을 그린다
  - 사진은 최근 리포트 5개에만 남기고 그보다 오래된 리포트에서는 뗀다(기기 저장소 약 5MB)
  - `photosNote` 20개 언어 문구를 "메모에만 붙고 보내지 않음"으로 바꾼다
- 하지 않는 것
  - `/api/extract`·`/api/triage`·`/api/report/clinician`·센터 요청에 사진 보내기(요청 형태 변경 없음, 백엔드 변경 없음)
  - 사진 확대 보기·회전 보정, `REPORT_FIELDS`에 `photos` 더하기(서버 계약과 parity에 들어가므로)

## 화면·파일
- S-05 `/intake`, S-11 `/report/new`, `/report/:id`. 경로·API 변경 없음
- `src/components/common.tsx`(`PhotoPicker`, `shrinkPhoto`), `src/state/AppState.tsx`(`photos`, `setPhotos`, 사진 남기는 리포트 수), `src/domain/templates.ts`(`ClinicianReport.photos?` 타입만, 출력 변경 없음), `src/pages/worker/Intake.tsx`, `src/pages/worker/Report.tsx`, `src/i18n/*.ts`(`photosNote`), `README.md`
- 새 문구 키 없음(체크 이름은 `photosTitle`, 한국어 리포트는 `사진`). 새 클래스 없음(`.photos`·`.photo` 재사용)

## 완료 기준
- [x] `npm run build` 통과, `cd app-front && npm run build` 통과
- [x] `/intake`에서 네 장을 고르면 세 장만 남고, `/result`까지 가면 `umn.session.photos`가 3개이고 `intake`에는 사진 데이터가 없다
- [x] `/report/new`에 `사진 (3)` 체크가 보이고, 만들면 `/report/:id`에 사진 3장이 보이며 `umn.device.demo`의 리포트에 `photos`가 있다
- [x] 흐름 동안 사진 데이터를 실은 요청이 없다
- [x] en·vi·ko, 360px에서 가로 스크롤 없음

## 결과
- `npm run build` → 통과(청크 크기 경고만). `cd app-front && npm run build` → 통과
- Playwright 헤드리스 Chromium, 단독 모드, 360px·움직임 줄이기, en·vi·ko: `/intake` 사진 4장 → 3장, 각주 문구 확인 → `/result`에서 세션 사진 3개·`intake`에 `data:image` 없음 → `/report/new` 체크 목록 끝에 `사진 (3)` → `/report/:id` 한국어 화면에 `사진` 줄 썸네일 3장(긴 변 384px 원본은 그대로) → 기기 저장소 36KB, 사진 붙은 리포트 1개. POST 본문 0건. `scrollWidth` 360
- 결정: 사진은 `REPORT_FIELDS`가 아니라 리포트를 만든 뒤 브라우저에서 붙인다. 서버 계약·`parity.json`이 그대로이고 API 모드에서도 사진이 서버로 가지 않는다
- 결정: JPEG로 바꿀 때 흰 바탕을 깐다(투명 PNG가 검게 되는 것 방지)

## 메모
- backlog 10의 "사진은 메모리에만, 저장하지 않음" 결정을 이 항목이 바꾼다
- `photosNote` 외국어 문구는 기계 번역 초안이다. en·vi 포함 원어민 검수가 필요하다
- 기기 저장소가 가득 차면 `writeJson`이 조용히 실패한다. 사진 남기는 리포트 수(5)로 막아 두었고, 더 필요하면 IndexedDB로 옮기는 항목을 따로 만든다
