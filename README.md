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

> 사람이 실행하는 명령 요약이다. 규칙의 원본은 [Git Flow](docs/GIT-FLOW.md)다. `<...>`는 상황에 맞게 바꿔 입력한다(`<`, `>` 기호는 지운다).

0. 최초 1회 설정
    - 커밋에 기록될 이름과 이메일을 등록한다. GitHub 계정 이메일을 사용한다.
        ```sh
        git config --global user.name "<내 이름>"
        git config --global user.email "<GitHub 계정 이메일>"
        ```
    - GitHub Personal Access Token을 발급받아 로컬에 저장하거나 `gh auth login`으로 인증한다.

1. 레포지토리 클론과 훅 설치
    - 클론은 처음 한 번만 한다. 훅은 커밋 trailer와 main·develop 직접 push를 검사한다.
        ```sh
        git clone <원격 레포지토리 URL>
        cd <레포지토리 폴더 이름>
        git config core.hooksPath .githooks
        ```

2. 브랜치 생성 및 체크아웃
    - main·develop에는 직접 push하지 않는다. 작업 전 develop을 최신화한 뒤 새 브랜치를 만든다.
        ```sh
        git switch develop
        git pull origin develop
        git switch -c <브랜치 이름>
        ```
    - 브랜치 이름은 영어로 쓰고 띄어쓰기는 `-`로 쓴다. 영역은 `frontend`·`backend`·`modeling`이다.

        | 목적 | 이름 규칙 | 생성 |
        |---|---|---|
        | 백로그 작성 | `backlog/<영역>/phase-XX` | 사람 |
        | 구현 | `feature/<영역>/phase-XX-<기능>` | 승인 후 `scripts/git_flow.py start`가 생성 |
        | 릴리스 | `release/<버전>` | 사람 |

    - 이미 있는 브랜치로 이동할 때는 `git switch <브랜치 이름>`, 현재 브랜치 확인은 `git branch`다.

3. 스테이징 및 커밋
    - 변경 사항을 확인하고 이번 커밋에 넣을 파일만 고른다.
        ```sh
        git status
        git diff
        git add <파일 경로>
        git commit
        ```
    - 백로그 커밋은 phase 문서만 포함하며 승인 trailer가 면제된다. 구현 커밋은 변경 이유를 제목으로 쓰고 다음 trailer를 남긴다.
        ```text
        [<영역>/phase-XX] <변경 이유>

        Backlog: backlog/<영역>/phase-XX.md
        Backlog-PR: https://github.com/<OWNER>/<REPO>/pull/<번호>
        Backlog-Revision: <백로그 PR 병합 SHA>
        Tested: <실제 실행한 명령과 결과>
        ```
    - 커밋 기록은 `git log --oneline`으로 확인한다.

4. 푸쉬
    - develop이 아닌 내 작업 브랜치로 push하는지 확인한다.
        ```sh
        git push -u origin <브랜치 이름>   # 처음 push할 때
        git push                         # 이후
        ```

5. PR
    - 대상은 `base: develop`이다. 템플릿은 [백로그](.github/PULL_REQUEST_TEMPLATE/backlog.md)·[구현](.github/PULL_REQUEST_TEMPLATE/implementation.md) 중 하나를 쓴다. PR 생성 URL에 `?template=backlog.md` 또는 `?template=implementation.md`를 붙이면 자동으로 채워진다.
    - 백로그 PR은 `.github/git-flow.json`의 approver가 최신 head를 승인한 뒤 병합한다. 병합 후 그 PR에 `implement backlog/<영역>/phase-XX.md <병합 SHA>` 댓글을 남기고 AI에게 PR 번호와 댓글 ID를 지정해 구현을 요청한다.
    - 리뷰 반영은 같은 브랜치에서 3~4번을 반복하면 PR에 반영된다.

6. PR 병합 후 정리
    - develop을 최신화하고 다 쓴 브랜치를 삭제한다. 다음 작업은 다시 2번부터 시작한다.
        ```sh
        git switch develop
        git pull origin develop
        git branch -d <브랜치 이름>
        ```

7. Tips
    - 작업 전 develop에 새 변경이 있는지 확인해 origin과 로컬의 차이를 줄인다.
