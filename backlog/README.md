# 영역별 백로그

백로그는 아래 세 영역으로 분리한다. 각 영역 안의 phase Markdown 문서는 사용자가 추후 작성한다.

- [프론트](frontend/README.md)
- [백엔드](backend/README.md)
- [모델링](modeling/README.md)

권장 파일명은 각 폴더의 `phase-01.md`, `phase-02.md` 등이다. 번호는 영역별로 독립적이며 같은 번호가 같은 일정이나 완료 상태를 뜻하지 않는다. 실제 phase 문서는 아직 없다.

각 문서는 해당 영역의 목표·범위·작업 체크리스트·완료 조건·검증 결과를 관리한다. 다른 영역이 먼저 제공해야 하는 계약이나 기능은 선행 phase 문서의 상대 경로와 필요한 산출물·완료 조건을 명시한다. 아직 작성되지 않은 의존 문서는 미정으로 표시하며 완료된 것으로 가정하지 않는다.

공유 API 계약의 원본은 루트 `shipyard-api-contract.md`다. 계약 변경 구현은 담당 영역 phase에 기록하고 다른 영역 phase에서 참조한다. 같은 작업의 상태를 여러 문서에 중복 관리하지 않는다. 이 README는 탐색용이며 상태 원장은 각 phase 문서다.

기존 `frontend.json`, `backend.json`, `modeling.json`, `shared.json`은 참고 초안으로 보존한다. 실제 phase와 동기화할 필요가 없다.

## 승인 절차

phase 문서는 사람이 `backlog/<영역>/phase-XX` 브랜치에서 PR로 제안하고 프로젝트 소유자가 승인·병합한다. 병합 후 사람이 같은 PR에 `implement <문서 경로> <병합 SHA>` 댓글을 남긴 다음 AI에게 작업을 요청한다. 문서 승인만으로 구현을 시작하지 않는다. 승인 범위 변경은 재승인이 필요하다. 자세한 규칙은 [Git Flow](../docs/GIT-FLOW.md)를 따른다.

## 문서 검사

`python3 scripts/harness.py check`로 phase Markdown 구조와 의존성을 검사하고, `python3 scripts/harness.py board`로 체크리스트 현황을 조회한다. 필수 섹션과 링크 형식은 [하네스 안내](../docs/HARNESS.md#최소-문서-형식)를 따른다. 실제 문서가 없으면 SKIP이며 자동 생성하지 않는다. 이 검사는 구현 승인이나 제품 품질 검사를 대신하지 않는다.
