# YardPilot 작업 규칙

사람용 약속은 `CONTRIBUTING.md`에 있다. AI도 같은 약속을 따른다.

- main에 직접 커밋·push하지 않는다. `<영역>/<내용>` 브랜치에서 작업한다.
- AI는 작업 브랜치에서 관련 테스트를 돌린 뒤 커밋, push, PR 생성(`gh pr create --base main`)까지 한다. 커밋 여부를 따로 묻지 않는다. 병합, 강제 push, main push, 훅·룰셋 우회는 하지 않는다.
- 폴더 경계를 지킨다. 프론트는 `frontend/`, 백엔드·시뮬레이터는 `backend/`, 차량 에이전트·학습은 `modeling/`. 영역별 문서는 각 `docs/`에, 공통 계약은 루트 `docs/api-contract.md`에 둔다.
- 작업 전 해당 영역 `AGENTS.md`, `docs/api-contract.md`, 영역 기획서(`<영역>/docs/proposal.md`)를 읽는다.
- phase 구현을 요청받으면 지정된 `<영역>/docs/phase-XX.md`의 범위만 구현하고, 실행한 테스트 명령과 결과를 같은 문서에 남긴다. 완료 기준이나 테스트를 지워서 통과시키지 않는다. 실패하면 고치거나 이유와 남은 일을 적는다.
- 공통 계약을 바꾸면 `docs/api-contract.md`, `fixtures/`, 쓰는 쪽 코드를 함께 고친다.
- 기존 패턴을 따르고 범위 밖 기능·의존성을 추가하지 않는다. 의존성 버전은 공식 문서·레지스트리로 확인해 고정하고 phase 문서에 출처와 날짜를 적는다.
- 커밋 제목은 변경 이유를 한 줄로 쓰고, 본문에 실행한 테스트와 결과를 적는다.
- PR 본문은 `.github/pull_request_template.md` 형식을 따른다.

불변식: 서버가 통행 상태의 원본이며 시간 만료는 점유 해제 증거가 아니다. 알 수 없는 예측은 null이다. 온라인 학습은 예측→완료 후 평가→업데이트 순서다. 시뮬레이션 시각과 네트워크 벽시계를 분리한다.

## 영역별 규칙

@frontend/AGENTS.md

@backend/AGENTS.md

@modeling/AGENTS.md
