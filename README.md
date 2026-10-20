# YardPilot

가상 조선소 차량 운행 지원 MVP. 프론트·백엔드·모델링별 작업 규칙과 검증 기준을 준비했다.

백로그는 사용자가 추후 작성하는 **phase별 Markdown 문서**를 기준으로 구현한다. phase의 범위·체크리스트·완료 조건을 따라 작업하고 검증 결과도 같은 문서에 기록한다.

- [영역별 백로그](backlog/README.md): [프론트](backlog/frontend/README.md) · [백엔드](backlog/backend/README.md) · [모델링](backlog/modeling/README.md)
- [하네스 운영 방식](docs/HARNESS.md)
- 영역별 규칙: [프론트](frontend/AGENTS.md) · [백엔드](backend/AGENTS.md) · [모델링](modeling/AGENTS.md)
- [공통 계약](shipyard-api-contract.md) · [프론트 기획](shipyard-frontend-proposal.md) · [백엔드 기획](shipyard-backend-proposal.md) · [기술·모델 기획](shipyard-technical-proposal.md)

기존 `backlog/*.json`은 참고 초안이며 phase 문서와 이중 관리할 필요가 없다. 기존 Python CLI와 CI는 JSON 도구 자체만 검사하며 제품 구현의 필수 절차가 아니다. 사용법은 [참고 문서](docs/JSON-HARNESS-REFERENCE.md)에 보존했다.

## 승인 후 구현

사람이 백로그 PR을 제출하고 소유자가 승인·병합한 뒤, 사람이 AI에게 해당 버전의 구현을 요청해야 작업 브랜치를 생성할 수 있다. AI는 구현·검증·커밋·PR 초안까지만 담당하며 PR 제출과 병합은 사람이 한다. [Git Flow와 설정](docs/GIT-FLOW.md)을 따른다. 설정되지 않은 승인 정보는 구현 시작을 차단한다.

## Git Cheat Sheet

> 사람이 실행하는 명령 요약이다. 규칙의 원본은 [Git Flow](docs/GIT-FLOW.md), 소유자 전용 설정은 [소유자 운영 문서](docs/GIT-OWNER.md)다. `<...>`는 상황에 맞게 바꿔 입력한다(`<`, `>` 기호는 지운다). 모든 명령은 저장소 최상위 폴더에서 실행한다.

### 처음 한 번

```sh
git config --global user.name "<내 이름>"
git config --global user.email "<GitHub 계정 이메일>"
gh auth login                        # GitHub CLI 로그인. 스크립트가 PR·댓글을 조회·생성할 때 쓴다
git clone <원격 레포지토리 URL>
cd <레포지토리 폴더 이름>
git config core.hooksPath .githooks  # main·develop 직접 커밋·push를 막는 훅
```

### 외울 명령 3개

| 명령 | 언제 |
|---|---|
| `python3 scripts/submit_pr.py` | 내 브랜치의 커밋을 push하고 develop 대상 PR을 만들 때. 열린 PR이 있으면 push만 한다 |
| `python3 scripts/request_impl.py backlog/<영역>/phase-XX.md` | 백로그 PR이 병합된 뒤 AI에게 구현을 맡기기 전에 |
| `python3 scripts/cleanup_branches.py` | PR이 병합된 뒤 develop을 최신화하고 다 쓴 브랜치를 지울 때 |

셋 다 `--dry-run`을 붙이면 무엇을 할지 먼저 보여 주고 아무것도 바꾸지 않는다.

### phase 하나의 흐름

1. **백로그 작성** — develop에서 브랜치를 만들고 phase 문서만 커밋한다. 영역은 `frontend`·`backend`·`modeling`이다.
    ```sh
    git switch develop
    git pull --ff-only origin develop
    git switch -c backlog/<영역>/phase-XX
    # backlog/<영역>/phase-XX.md 작성
    git add backlog/<영역>/phase-XX.md
    git commit -m "[<영역>/phase-XX] <이 phase가 필요한 이유>"
    python3 scripts/submit_pr.py
    ```
2. **승인** — 소유자가 PR을 확인하고 **Squash and merge**로 병합한다. 병합되면 `python3 scripts/cleanup_branches.py`.
3. **구현 요청** — 아래 명령 후 AI 채팅에 "backlog/<영역>/phase-XX.md 구현해줘"라고 쓴다. AI가 승인을 확인하고 `feature/` 브랜치를 만들어 구현·테스트·커밋·PR 초안까지 한다.
    ```sh
    python3 scripts/request_impl.py backlog/<영역>/phase-XX.md
    ```
4. **구현 PR 제출** — AI 작업이 끝나면 그 feature 브랜치에서 `python3 scripts/submit_pr.py`. 리뷰 반영은 AI에게 요청한 뒤 같은 명령을 다시 실행한다.
5. **병합 후 정리** — Squash and merge로 병합되면 `python3 scripts/cleanup_branches.py`. 다음 phase는 1번부터.

### 하지 말 것

- main·develop에 직접 커밋·push하지 않는다. 훅이 막는다.
- GitHub 웹에서 PR을 만들지 않는다. base를 main으로 잘못 고르기 쉽다. `submit_pr.py`는 항상 develop을 대상으로 한다.
- 병합 버튼은 **Squash and merge**만 쓴다. 다른 방식은 막혀 있다.
- 원격 브랜치를 직접 지우지 않는다(`git push --delete`는 훅이 막는다). 병합하면 GitHub가 지우고, 로컬은 `cleanup_branches.py`가 지운다.
- 구현 커밋은 승인 trailer가 필요하므로 AI가 만든다. 사람이 쓰는 백로그 커밋은 phase 문서만 담으면 trailer가 필요 없다.

### 상태 확인

```sh
git status          # 현재 브랜치와 바뀐 파일
git diff            # 아직 커밋하지 않은 변경 내용
git log --oneline   # 커밋 기록
git branch          # 로컬 브랜치 목록, * 가 현재 브랜치
```
