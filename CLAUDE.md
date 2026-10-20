# YardPilot 작업 계약

사용자가 작성하는 phase별 Markdown 문서를 백로그 기준으로 사용하는 하네스다. 제품 구현은 아직 시작하지 않았다.

- 구현 전 `docs/GIT-FLOW.md`를 따른다. 소유자가 최신 head를 승인했거나 직접 병합한 백로그 PR, 병합 후 사람의 구현 요청 댓글이 모두 있어야 `scripts/git_flow.py start`로 작업 브랜치를 생성한다. 승인만으로 자동 시작하지 않는다. AI는 push·PR 제출·병합·강제 push·브랜치 삭제·보호 규칙 우회를 하지 않으며 PR 초안까지 작성한다.
- AI가 작성한 변경(phase 문서 초안·정책·구현)은 해당 작업 브랜치에서 관련 검증을 실행한 뒤 커밋까지 항상 진행한다. 커밋 여부를 따로 묻지 않는다. main/develop이나 브랜치 유형에 맞지 않는 파일은 커밋하지 않고, 훅을 우회하지 않으며, 실패한 검증은 `Not-tested`나 차단 사유로 기록한다.
- `scripts/git_flow.py start`의 원격 검증을 통과한 feature 브랜치에서만 제품을 구현한다. 설정 누락·인증 실패는 차단 상태다. 문서의 approved 표기나 JSON 초안을 승인 근거로 신뢰하지 않는다. 구현 재개 전 `scripts/git_flow.py check-context`를 실행한다.
- 하네스·정책 유지보수 요청은 제품 구현 승인이 아니다. 하네스 변경으로 제품 gate를 우회하지 않는다.
- 모든 구현 커밋에 `Backlog`, `Backlog-PR`, `Backlog-Revision` trailer를 기록한다. 승인 범위 변경은 별도 백로그 PR 재승인과 새 요청이 필요하다.
- 먼저 `docs/HARNESS.md`, `shipyard-api-contract.md`, 해당 영역 기획서와 백로그를 읽는다.
- 영역별 규칙은 아래 import로 항상 로드된다. 프론트는 `frontend/AGENTS.md`, 백엔드·`simulator/`는 `backend/AGENTS.md`, 모델링·`agents/`·`training/`은 `modeling/AGENTS.md`를 따른다.
- 백로그는 `backlog/frontend/`, `backlog/backend/`, `backlog/modeling/`으로 분리한다. phase 번호·상태는 영역별로 관리하고 영역 간 의존성은 문서 경로로 연결한다.
- 사용자가 지정한 phase Markdown 문서에서 범위·선행 조건·완료 기준을 확인하고 해당 범위만 구현한다. phase 문서는 사용자가 추후 작성하며 미리 생성하거나 구현을 시작하지 않는다.
- 지정된 phase Markdown 문서가 구현 범위·순서·상태의 단일 원본이다. 기존 backlog JSON은 참고 초안이며 CLI 실행이나 JSON 동기화는 필수가 아니다. 완료 조건·검증 항목을 삭제해 검사를 통과시키지 않는다. 제품 완료와 하네스 검증 통과를 구분한다.
- 공유 계약 변경은 해당 phase 문서에서 결정 근거를 기록하고 세 영역의 fixture(루트 `fixtures/`)·생성 타입·소비자를 함께 갱신한다.
- 테스트를 실행하고 명령·결과·완료 조건별 증빙을 phase 문서에 남긴 뒤 완료로 표시한다. 구현 완료·PR 대기와 병합 완료를 구분한다. 실패는 수정하거나 차단 이유와 남은 작업을 기록한다.
- 독립 작업은 병렬 수행할 수 있지만 같은 phase 문서의 상태 갱신은 충돌하지 않도록 담당자가 모아 반영한다. 다른 작업자의 변경을 되돌리지 않는다.
- 기존 패턴을 우선 사용하고 범위를 벗어난 기능·의존성을 추가하지 않는다. 라이브러리 버전은 구현 작업에서 공식 문서로 확인하고 잠근다.
- 정리·리팩터링은 계획과 기존 동작 회귀 검증을 먼저 작성한다.
- 커밋은 변경 이유를 제목으로 쓰고 필요한 `Constraint`, `Rejected`, `Confidence`, `Scope-risk`, `Directive`, `Tested`, `Not-tested` Lore trailer를 남긴다.

불변식: 서버가 통행 상태의 원본이며 시간 만료는 점유 해제 증거가 아니다. 알 수 없는 예측은 null이다. 온라인 학습은 예측→완료 후 평가→업데이트 순서다. 시뮬레이션 시각과 네트워크 벽시계를 분리한다.

## 영역별 규칙

@frontend/AGENTS.md

@backend/AGENTS.md

@modeling/AGENTS.md
