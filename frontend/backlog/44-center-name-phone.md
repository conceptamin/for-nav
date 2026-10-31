# 44. 센터 정식 이름과 기관 연락처

상태: 완료
의존: 없음

## 목표
2026-10-31 사용자 요청: 앱에 보이는 센터 이름 `울산외국인주민·근로자지원센터`를 정식 이름 `울산외국인주민·근로자통합지원센터`로 고치고, 센터 전화번호 1577-2818과 울산시 의료비 지원사업 연락처 052-235-7100을 넣는다. 지금까지 두 연락처는 미확인이라 `phone: null`이었고 보험·지원 화면(S-11)에 "센터 상담으로 확인하세요"만 보였다.

## 범위
- 하는 것: 20개 언어의 `inst.center`·`cenConsent` 센터 이름, 센터 화면 머리글, `domain/coverage.ts`의 `CENTER`·`ULSAN` 번호, 백엔드 `rules/coverage.py`의 같은 상수, `parity.json` 재생성, 두 README의 연락처 항목과 API 예시
- 하지 않는 것: `지원센터에 문의`처럼 이름을 줄여 부르는 메뉴·제목 문구, 화면 배치

## 화면·파일
- S-11 `/coverage`: 연락처 칸에 센터 ☎️ 1577-2818, 울산시 의료비 지원 ☎️ 052-235-7100 버튼(기존 `tel:` 버튼 그대로)
- S-12 `/center-request`: 동의 문장의 센터 이름
- C-01 센터 화면 머리글: `울산외국인주민·근로자통합지원센터 · 의료지원`
- `src/i18n/*.ts`(20개), `src/domain/coverage.ts`, `src/pages/center/Center.tsx`, `README.md`
- `backend/app/rules/coverage.py`, `backend/tests/fixtures/parity.json`, `backend/tests/test_api.py`, `backend/README.md`
- 새 문구 키 없음

## 완료 기준
- [x] `npm run build` 통과
- [x] 빌드 결과에 옛 이름 `근로자지원센터`가 없음
- [x] `parity.json` 재생성 후 `uv run pytest` 통과

## 결과
- `npm run build` → 통과
- `npx rolldown scripts/dump-fixtures.ts ... && TZ=Asia/Seoul node dump.mjs > ../backend/tests/fixtures/parity.json` → 바뀐 값은 `center`·`ulsan`의 `phone`과 `generatedAt`뿐
- `uv run ruff check .`, `uv run ruff format --check .` → 통과. `uv run pytest` → 3118 passed
- 브라우저 확인은 하지 못했다(미리보기가 작업 worktree가 아닌 원래 checkout을 띄움). 빌드 번들에 새 이름·번호가 들어간 것만 확인했다.
- 결정: 다른 언어도 '통합'을 옮겨 넣었다(사용자 결정). 센터 화면 머리글의 띄어쓰기 `울산 외국인주민·근로자 통합지원센터`도 같은 표기로 맞췄다.
- 결정: 프론트가 원본인 `domain/coverage.ts`를 바꿨으므로 백엔드 상수와 README 예시 테스트를 같은 PR에서 고쳤다(사용자 결정, 한 PR).

## 메모
- en·vi를 뺀 언어의 '통합' 번역(예: en `Integrated Support Centre`, ru `Объединённый центр`, uz `yagona markazi`)은 기계 번역 초안이다. 원어민 검수가 필요하다.
- 번호는 사용자가 2026-10-31에 준 값이다. 발표 전 다른 기관 대표번호와 함께 재확인한다(`README.md` "확인이 필요한 값").
