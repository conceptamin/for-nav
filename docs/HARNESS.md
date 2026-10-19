# Phase 문서 기반 개발 하네스

백로그는 사용자가 나중에 작성하는 **phase별 Markdown 문서**로 관리한다. 구체적인 phase와 구현 순서는 미리 확정하지 않는다. 기본 위치는 `backlog/frontend/`, `backlog/backend/`, `backlog/modeling/`이며 각 영역 안에 phase 문서를 작성한다. 사용자가 별도 위치를 지정하면 이를 따른다. [백로그 안내](../backlog/README.md)에서 영역별 문서로 이동한다.

## 구현 흐름

1. [승인 기반 Git Flow](GIT-FLOW.md)에 따라 소유자가 승인·병합한 백로그 PR과 병합 후 사람의 구현 요청을 확인한다. `scripts/git_flow.py start` 검증을 통과한 작업 브랜치에서만 구현한다. 지정된 phase 문서와 관련 기획서·공통 API 계약을 읽는다.
2. 해당 phase의 목표·범위·선행 조건·완료 기준을 확인한다.
3. 프론트·백엔드·모델링 중 해당 영역 규칙을 적용해 구현한다.
4. 변경 동작을 검증하고 실행 명령·결과·남은 제약을 phase 문서에 기록한다.
5. 검증된 항목만 완료로 표시한다. 후속 phase는 요청된 범위에 따라 진행한다.

각 phase 문서는 한 영역의 목표, 작업 체크리스트, 의존성, 완료 조건, 검증 결과를 관리한다. 영역별 phase 번호와 진행 상태는 독립적이다. 다른 영역의 선행 작업은 해당 문서 경로와 필요한 산출물로 연결하며 상태를 중복 기록하지 않는다. 별도 JSON 상태 기록이나 고정 ID는 요구하지 않는다. 문서가 아직 없다는 이유로 임의의 phase를 생성하거나 초기 초안 작업을 자동 시작하지 않는다.

## 영역별 하네스

| 영역 | 규칙 | 구현 경로 | 검증 기준 |
|---|---|---|---|
| 프론트 | frontend/AGENTS.md | frontend/ | 타입·lint·빌드, 상태 복구, 실제 브라우저·Canvas·접근성 |
| 백엔드 | backend/AGENTS.md | backend/, simulator/, tests/backend/ | API·권한·트랜잭션·경로·예약·재시작, Ruff·mypy·pytest |
| 모델링 | modeling/AGENTS.md | agents/, training/, tests/modeling/ | 데이터 누수·시간순 평가·중복 학습·복구·재현성·추론 비용 |

`simulator/` 작업에는 백엔드 규칙, `agents/`·`training/` 작업에는 모델링 규칙을 함께 읽는다. 공유 계약 변경은 해당 phase에 근거를 기록하고 영향을 받는 영역의 타입·fixture·소비자를 함께 검증한다.

제품 검증 도구와 실행 명령은 아직 구성되지 않았다. 각 영역 구현 시 실제 명령과 호환 버전·lockfile을 마련한다. 목표 성능을 측정 결과로 표시하거나 빈 테스트로 완료 처리하지 않는다.

## Markdown 검사 도구

`backlog/*.json`의 27개 항목은 기획서에서 추출한 **참고 초안**이다. phase 문서를 작성할 때 필요한 내용을 가져올 수 있으며 구현 순서·범위·상태의 원본으로 사용하지 않는다. phase 문서와 JSON을 이중 관리할 필요가 없다.

`scripts/harness.py`는 phase Markdown을 읽기 전용으로 검사한다. JSON을 읽거나 동기화하지 않으며 문서의 상태도 변경하지 않는다. 승인·착수 검사는 `git_flow.py`가 담당한다.

```sh
python3 scripts/harness.py check
python3 scripts/harness.py board --lane backend
python3 scripts/harness.py check backlog/backend/phase-01.md
python3 scripts/harness.py check plans/custom-phase.md
python3 -m unittest discover -s tests/harness -v
```

기본 검색 대상은 `backlog/{frontend,backend,modeling}/phase-*.md`다. 별도 위치의 문서는 저장소 기준 경로를 명시한다. `--lane`과 명시 경로는 함께 사용하지 않는다. 대상이 없으면 `SKIP`과 종료 코드 0을 반환하며 문서를 생성하지 않는다. 잘못된 문서·누락된 명시 경로는 종료 코드 1, 잘못된 CLI 사용은 2다. 기본 CI도 같은 `check` 명령을 실행한다.

### 최소 문서 형식

다음 여섯 `##` 섹션은 각각 비어 있지 않아야 한다. 작업 체크리스트와 완료 조건에는 `- [ ]` 또는 `- [x]` 항목이 하나 이상 필요하다. 추가 섹션은 허용하지만 동일 이름의 섹션은 중복할 수 없다. 코드 블록과 HTML 주석은 검사 대상에서 제외하므로 검증 결과에는 블록 밖에도 설명을 남긴다.

아래는 형식 예시이며 실제 백로그나 구현 승인이 아니다.

```markdown
# Phase 제목

## 목표
달성할 결과를 작성한다.

## 범위
포함되는 작업과 제외되는 작업을 작성한다.

## 작업 체크리스트
- [ ] 구현할 작업

## 의존성
없음

## 완료 조건
- [ ] 관찰 가능한 수용 조건

## 검증 결과
미실행. 구현 후 실행 명령·결과·완료 조건별 증거·남은 제약을 기록한다.
```

의존 phase는 의존성 섹션에 `[선행 phase](../frontend/phase-01.md)`처럼 해당 문서 기준 상대 Markdown 링크로 기록한다. 링크는 공백 없는 경로를 사용한다. 필요한 산출물도 함께 설명한다. 참조 문서에도 같은 형식을 적용하며, 영역 필터와 관계없이 재귀 검사해 순환을 거부한다. 링크 대상 누락은 오류다. 아직 작성되지 않은 의존성은 `미정: [선행 phase](../frontend/phase-01.md)`처럼 같은 줄에 `미정`을 명시하면 경고로 남긴다. 링크 없이 미정 사유를 기록할 수도 있다. 저장소 밖 경로·심볼릭 링크와 외부 URL은 의존 phase로 허용하지 않는다.

`board`는 선택 문서의 작업 및 완료 조건 체크 수를 보여준다. 체크 수로 승인 여부, 시작 가능 여부, 제품 완료나 병합 상태를 추론하지 않는다. `PASS`도 문서 구조의 유효성만 의미한다. 검증 기록의 충분성·최신성·진실성, 의존 산출물의 실제 준비 여부는 별도 리뷰로 확인한다.

기존 JSON용 `start`, `block`, `resume`, `run`, `done`, `next` 명령은 제거했다. 검증은 실제 제품 명령으로 실행하고 결과를 phase 문서에 직접 기록한다. [이전 도구 전환 안내](JSON-HARNESS-REFERENCE.md)를 참고한다.
