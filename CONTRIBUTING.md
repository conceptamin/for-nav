# 작업 약속

복잡한 절차 없이 아래만 지킨다.

## 1. main은 PR로만 바꾼다

- main에 직접 커밋·push하지 않는다. 로컬 훅과 GitHub 룰셋이 둘 다 막는다.
- 작업은 브랜치에서 하고 PR을 연다. **1명 이상 승인**과 CI 통과 후 병합한다.
- 브랜치 이름은 `<영역>/<내용>` 형식으로 쓴다. 예: `frontend/map-view`, `backend/reservation`, `modeling/baseline`, `docs/api-contract`.

## 2. 폴더를 지킨다

| 폴더 | 무엇 |
|---|---|
| `frontend/` | 프론트 코드. 문서는 `frontend/docs/` |
| `backend/` | 백엔드·시뮬레이터 코드. 문서는 `backend/docs/` |
| `modeling/` | 차량 에이전트·학습 코드. 문서는 `modeling/docs/` |
| `docs/` | 세 영역이 같이 보는 문서(공통 API 계약) |
| `fixtures/` | 세 영역이 같이 쓰는 테스트 데이터 |

- 내 영역 밖 폴더를 고쳐야 하면 PR에 적고 그 영역 담당에게 리뷰를 받는다.
- 공통 계약(`docs/api-contract.md`)을 바꾸면 `fixtures/`와 쓰는 쪽 코드를 같은 PR에서 함께 고친다.

## 3. phase 문서

- 각 영역의 `docs/phase-XX.md`에 쓴다. 번호는 영역마다 따로 매긴다.
- 들어갈 내용: 목표, 범위(포함·제외), 할 일 체크리스트, 완료 기준, 검증 결과.
- 다른 영역에 의존하면 그 문서 경로를 적는다. 예: `../../backend/docs/phase-02.md`
- 구현이 끝나면 실행한 테스트와 결과를 같은 문서에 남긴다.

## 4. 테스트

- PR을 올리기 전에 내 영역 테스트를 돌린다. 명령은 각 영역의 `AGENTS.md`에 있다.
- CI가 PR마다 프론트·백엔드 테스트를 자동으로 돌린다. 실패하면 병합할 수 없다.

## 처음 한 번

```sh
git clone <저장소 URL>
cd yardpilot
git config core.hooksPath .githooks
```

마지막 줄이 main 직접 커밋·push를 막는 로컬 훅을 켠다.

## 매번 하는 일

```sh
git switch main
git pull
git switch -c <영역>/<내용>
# 작업하고 테스트
git add <파일>
git commit -m "<무엇을 왜 바꿨는지>"
git push -u origin <영역>/<내용>
gh pr create --base main --fill
```

리뷰를 받고 승인되면 GitHub에서 **Squash and merge**로 병합한다. 병합된 원격 브랜치는 자동으로 지워진다.
