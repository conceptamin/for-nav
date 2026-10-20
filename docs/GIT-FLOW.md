# 승인 기반 Git Flow

모든 참여자가 따르는 흐름이다. 처음이라면 [README의 Git 치트시트](../README.md#git-cheat-sheet)부터 본다. approver 설정·정책 브랜치·원격 보호처럼 소유자만 다루는 내용은 [소유자 운영 문서](GIT-OWNER.md)에 있다.

## 권한과 순서

1. 사람이 `backlog/<영역>/phase-XX` 브랜치에서 phase Markdown만 작성하고 develop으로 PR을 제출한다.
2. `.github/git-flow.json`의 approver로 지정된 프로젝트 소유자가 최신 PR head를 승인하고 사람이 병합하거나, approver가 직접 병합한다. 병합 시점의 head가 최종이므로 approver의 병합은 최신 head 승인으로 인정한다(1인 저장소는 자기 PR에 리뷰 승인을 남길 수 없다). 승인 댓글이나 문서의 approved 필드는 승인 증거가 아니다.
3. 병합 이후 사람이 `python3 scripts/request_impl.py <문서 경로>`로 그 PR에 `implement <문서 경로> <병합 SHA>` 댓글을 남기고 AI에게 "<문서 경로> 구현해줘"라고 요청한다. 댓글은 실행한 사람의 계정으로 남으며 그 계정은 저장소 참여자(OWNER/MEMBER/COLLABORATOR)여야 한다. 이 댓글은 실행 요청의 감사 기록이다. 승인만으로 자동 착수하지 않는다.
4. AI는 아래 start 명령으로 승인 PR과 요청 댓글을 읽기 전용으로 찾아 승인과 요청을 검증한 후 origin/develop에서 작업 브랜치를 생성한다. 네트워크·인증 실패나 설정 누락도 차단한다.
5. 승인 범위만 구현하고 테스트한다. 검증 결과는 phase 문서에 기록하되 목표·범위·수용 기준을 바꾸지 않는다. 범위 변경은 별도 백로그 PR에서 재승인받고 새 요청을 받아야 한다.
6. AI는 자신이 작성한 변경을 해당 작업 브랜치에서 검증한 뒤 커밋까지 항상 진행하고(별도 확인 없이) PR 본문 초안을 작성한다. 사람만 push·PR 제출·리뷰·병합을 한다. AI는 자동 PR 생성, 병합, 보호 설정 변경, force push, 브랜치 삭제를 하지 않는다.
7. 병합 후 사람이 작업 브랜치를 삭제한다. 구현 완료는 PR 대기 상태이며, 실제 병합 완료와 구분한다. main/develop은 삭제하지 않는다.

## 브랜치

| 브랜치 | 기준 | PR 대상 | 담당 |
|---|---|---|---|
| backlog/<영역>/phase-XX | develop | develop | 사람 |
| feature/<영역>/phase-XX-<기능> | develop | develop | 승인 후 AI 구현, 사람 PR |
| policy/<slug> | develop | develop | 하네스·운영 규칙만; AI 초안 가능, approver가 직접 PR |
| release/<버전> | develop | main, 변경분을 develop에 역반영 | 사람 |
| hotfix/<영역>/phase-XX-<수정> | main | main, develop 역반영 | 사람; 현재 자동 gate는 차단 |

영역 이름은 기존 디렉터리와 맞춰 frontend/backend/modeling을 쓴다. 별도 장기 영역 브랜치는 만들지 않는다. release의 승인·병합 권한은 원격 보호 규칙으로 제한한다. hotfix는 승인 검증을 우회하는 통로로 사용하지 않는다. 현재 구현 시작 CLI는 feature만 지원하며 hotfix 지원은 별도 정책 변경으로 다룬다.

정책 브랜치의 허용 파일과 제출 규칙은 [소유자 운영 문서](GIT-OWNER.md#정책-브랜치)를 따른다.

## 설정 및 실행

Git 저장소·GitHub 원격·develop이 존재해야 한다. origin은 github.com HTTPS/SSH 주소이거나, `ssh -G` 기준 hostname이 github.com인 SSH 별칭이어야 한다. `.github/git-flow.json`의 `repository`·`approver`는 소유자가 채운다([소유자 운영 문서](GIT-OWNER.md#approver와-저장소-설정)). 설정이 비면 구현 시작이 차단된다. GitHub CLI(`gh auth login`)로 인증해야 스크립트가 API를 조회한다.

클론 후 로컬 훅을 설치한다:

```sh
git config core.hooksPath .githooks
```

### 구현 요청

사람은 백로그 PR이 병합된 뒤 아래 명령으로 구현 요청 댓글을 남긴다. AI는 이 스크립트를 실행하지 않는다(`--dry-run` 제외).

```sh
python3 scripts/request_impl.py backlog/backend/phase-01.md --dry-run   # 찾은 PR과 남길 댓글만 출력
python3 scripts/request_impl.py backlog/backend/phase-01.md             # 댓글을 남기고 start 기준으로 다시 검증
```

- 문서를 담아 develop에 가장 최근 병합된 `backlog/` PR과 그 병합 SHA를 찾는다. 다른 PR을 쓰려면 `--pr <번호>`를 붙인다.
- 댓글을 달기 전에 approver 승인, phase 문서만 포함, 승인 문서가 PR head·현재 develop과 같은지를 start와 같은 코드로 확인한다. 문서가 바뀌었으면 댓글을 달지 않고 재승인을 요구한다.
- 유효한 요청 댓글이 이미 있으면 새로 달지 않는다. 방금 단 댓글이 요청으로 인정되지 않으면(예: 저장소 참여자가 아닌 계정) 실패를 알린다.

### 작업 브랜치 생성

AI는 사람이 phase 구현을 요청하면 아래 명령으로 작업 브랜치를 만든다.

```sh
python3 scripts/git_flow.py start --backlog backlog/backend/phase-01.md --slug auth
python3 scripts/git_flow.py check-context
```

`--approval-pr`·`--request-comment`를 생략하면 start가 문서를 담은 최근 병합 백로그 PR과 그 PR의 유효한 요청 댓글 중 최신 것을 gh로 읽기 전용 조회한다. 찾은 값도 직접 지정한 값과 똑같이 전체 검증을 거친다. 요청 댓글이 없으면 브랜치를 만들지 않고 사람에게 `request_impl.py` 실행을 안내한다.

start는 깨끗한 작업 트리와 승인된 문서 원문을 요구한다. 승인 문서가 develop에서 변경됐으면 재승인이 필요하다. 작업 컨텍스트는 해당 worktree의 Git 디렉터리에 보관하며 버전 관리하지 않는다. 구현을 재개하기 전에 check-context를 실행한다. 커밋 훅은 승인 기록을 다시 조회한다.

구현 커밋은 변경 이유를 제목으로 쓰고 기존 Lore trailer와 다음 필수 참조를 기록한다:

```text
[backend/phase-01] 비인가 요청을 차단하기 위해 세션을 검증한다

Backlog: backlog/backend/phase-01.md
Backlog-PR: https://github.com/OWNER/REPO/pull/42
Backlog-Revision: <백로그 PR 병합 SHA>
Tested: 실제 실행한 명령과 결과
```

백로그 제안 커밋은 아직 승인 PR이 없으므로 승인 trailer 검사를 면제하며 phase 문서만 허용한다. 구현 PR은 `.github/PULL_REQUEST_TEMPLATE/implementation.md`를 사용한다. 모든 구현 커밋에 참조가 필요하며 merge commit도 예외가 아니다.

### PR 제출

사람은 작업 브랜치에서 아래 명령으로 push와 develop 대상 PR 생성을 한 번에 처리한다. AI는 이 명령을 실행하지 않는다.

```sh
python3 scripts/submit_pr.py --dry-run   # 검사와 제출 계획만 출력
python3 scripts/submit_pr.py             # push 후 PR 생성(열린 PR이 있으면 push만)
```

- backlog/·feature/·policy/ 브랜치만 받는다. main/develop·release·hotfix는 거부한다. 작업 트리가 깨끗하고 origin/develop보다 앞선 커밋이 있어야 한다.
- 사전 검사: backlog는 `harness.py check`, feature는 `git_flow.py check-context`, policy는 gh 계정이 `.github/git-flow.json`의 approver인지 확인한다. push는 pre-push 훅을 그대로 거친다.
- 본문은 `--body-file`, AI 초안 `<git-dir>/yardpilot-pr/<브랜치의 /를 __로 바꾼 이름>.md`, 로컬 `.github/PULL_REQUEST_TEMPLATE/` 템플릿 순으로 고른다. 로컬 템플릿을 쓰므로 main에 아직 없는 템플릿도 사용할 수 있다. 초안 첫 줄이 `# 제목`이면 PR 제목으로 쓰고, 없으면 첫 커밋 제목을 쓴다. 초안은 worktree의 Git 디렉터리에 두며 버전 관리하지 않는다.

### 병합과 정리

- develop 대상 PR은 **Squash and merge**만 쓴다. 룰셋이 다른 병합 방식을 막는다. PR 하나가 develop 커밋 하나가 되며 백로그 PR의 병합 SHA는 그 squash 커밋이다. main은 release 이력을 develop과 잇도록 merge commit만 허용한다.
- GitHub의 병합 후 head 브랜치 자동 삭제가 켜져 있어 원격 작업 브랜치는 병합과 함께 지워진다. pre-push 훅이 삭제 push를 막으므로 로컬에서 원격 브랜치를 지우지 않는다.
- 병합 후 사람이 아래 명령으로 develop을 최신화하고 로컬 브랜치를 지운다. squash 병합된 브랜치는 `git branch -d`가 미병합으로 보므로 이 스크립트를 쓴다. AI는 `--dry-run`만 실행한다.

```sh
python3 scripts/cleanup_branches.py --dry-run   # 지울 브랜치와 남길 이유만 출력
python3 scripts/cleanup_branches.py             # develop 전환·최신화 후 병합된 로컬 브랜치 삭제
```

- origin을 prune fetch한 뒤 develop에 병합된 PR의 head와 끝 커밋이 같은 로컬 브랜치만 지운다. 병합 후 새 커밋이 있거나 병합된 PR이 없는 브랜치와 main·develop은 남긴다.
- 현재 브랜치가 지울 대상이고 변경이 없으면 develop으로 전환해 `pull --ff-only`한 뒤 지운다. 지운 브랜치의 PR 초안과 승인 컨텍스트도 함께 지운다.

## 강제력과 원격 보호

로컬 훅은 우회 가능하며 AI와 사람의 신원을 구별하는 보안 경계가 아니다. CLAUDE.md는 AI의 행동 계약이고, 실제 원격 권한은 별도로 제한해야 한다. 사람 계정의 토큰을 AI에게 주면 API의 User 표기만으로 사람이 직접 요청했음을 증명할 수 없다. AI 세션에는 읽기 전용 자격 증명을 사용한다.

원격 보호 규칙(룰셋·필수 검사·병합 방식)과 CI의 한계는 [소유자 운영 문서](GIT-OWNER.md#원격-보호)에 있다.
