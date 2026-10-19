# 승인 기반 Git Flow

## 권한과 순서

1. 사람이 `backlog/<영역>/phase-XX` 브랜치에서 phase Markdown만 작성하고 develop으로 PR을 제출한다.
2. `.github/git-flow.json`의 approver로 지정된 프로젝트 소유자가 최신 PR head를 승인하고 사람이 병합하거나, approver가 직접 병합한다. 병합 시점의 head가 최종이므로 approver의 병합은 최신 head 승인으로 인정한다(1인 저장소는 자기 PR에 리뷰 승인을 남길 수 없다). 승인 댓글이나 문서의 approved 필드는 승인 증거가 아니다.
3. 병합 이후 저장소 참여자(OWNER/MEMBER/COLLABORATOR)가 그 PR에 `implement <문서 경로> <병합 SHA>` 댓글을 남긴다. 사람이 AI에게 문서·승인 PR 번호·댓글 ID를 지정해 작업을 요청한다. 이 댓글은 실행 요청의 감사 기록이다. 승인만으로 자동 착수하지 않는다.
4. AI는 아래 start 명령으로 승인과 요청을 검증한 후 origin/develop에서 작업 브랜치를 생성한다. 네트워크·인증 실패나 설정 누락도 차단한다.
5. 승인 범위만 구현하고 테스트한다. 검증 결과는 phase 문서에 기록하되 목표·범위·수용 기준을 바꾸지 않는다. 범위 변경은 별도 백로그 PR에서 재승인받고 새 요청을 받아야 한다.
6. AI는 커밋과 PR 본문 초안까지 작성한다. 사람만 push·PR 제출·리뷰·병합을 한다. AI는 자동 PR 생성, 병합, 보호 설정 변경, force push, 브랜치 삭제를 하지 않는다.
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

정책 브랜치는 하네스와 운영 규칙(`.github/`, `.githooks/`, `.gitignore`, `CLAUDE.md`, `README.md`, 영역별 `AGENTS.md`, `docs/`, `scripts/`, `tests/harness/`)만 바꾼다. 제품 코드·`backlog/`·`fixtures/`·`shipyard-*.md` 기획·계약서는 포함할 수 없고 파일 이동으로도 옮길 수 없다. 계약 변경은 phase 문서에서 fixture·소비자와 함께 다룬다. approval-gate는 PR 작성자가 approver인지 확인하며, 하네스 유지보수 요청은 제품 구현 승인이 아니다. 정책 PR의 gate도 base(develop)의 스크립트로 실행되므로 정책 PR이 자기 검사를 완화해 통과할 수 없다. policy 경로를 처음 도입하는 변경은 base에 아직 규칙이 없으므로 룰셋 적용 전에 소유자가 부트스트랩한다.

## 설정 및 실행

Git 저장소·GitHub 원격·develop이 존재해야 한다. origin은 github.com HTTPS/SSH 주소이거나, `ssh -G` 기준 hostname이 github.com인 SSH 별칭이어야 한다. `.github/git-flow.json`에 실제 `repository` (`owner/repo`)와 승인자의 GitHub `approver` 로그인명을 입력한다. 값을 추정하거나 AI가 임의로 승인자로 등록하지 않는다. GitHub CLI는 인증된 읽기 권한으로 API를 조회한다. 현재 null 설정은 의도적으로 구현을 차단한다.

저장소 연결 후 로컬 훅을 설치한다:

```sh
git config core.hooksPath .githooks
python3 scripts/git_flow.py start --backlog backlog/backend/phase-01.md --approval-pr 42 --request-comment 123456 --slug auth
python3 scripts/git_flow.py check-context
```

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

## 강제력과 원격 보호

로컬 훅은 우회 가능하며 AI와 사람의 신원을 구별하는 보안 경계가 아니다. CLAUDE.md는 AI의 행동 계약이고, 실제 원격 권한은 별도로 제한해야 한다. 사람 계정의 토큰을 AI에게 주면 API의 User 표기만으로 사람이 직접 요청했음을 증명할 수 없다. AI 세션에는 읽기 전용 자격 증명을 사용한다.

원격 저장소에서 main/develop에 필수 PR, 필수 승인, stale approval 무효화, 마지막 push 재승인, force push/삭제 금지, 우회 권한 제한을 적용한다. 백로그와 정책 파일에는 소유자의 CODEOWNERS 승인을 필수로 설정한다. 필수 상태 검사는 `Git flow / approval-gate` 및 `Backlog harness / harness`로 지정한다. 실제 UI의 check 이름을 확인한다. 소유자 로그인 확정 전 가짜 CODEOWNERS 항목은 생성하지 않는다.

위 보호는 `scripts/protect_branches.py`가 GitHub 룰셋 `yardpilot-protected-branches`로 적용한다. 룰셋은 우회 주체가 없어 관리자도 main/develop에 직접 push·삭제·force push할 수 없고, `approval-gate`가 feature→develop·backlog→develop·policy→develop·release→main/develop 외의 병합을 막는다. 상태 검사는 GitHub Actions(integration 15368) 결과만 인정한다. apply는 저장소 관리자 권한이 필요하며 소유자가 직접 실행한다. AI는 plan·check만 실행한다.

```sh
python3 scripts/protect_branches.py plan                          # 적용할 룰셋 출력, 네트워크 없음
python3 scripts/protect_branches.py apply --repo OWNER/REPO       # 소유자만: 생성 또는 같은 룰셋 갱신
python3 scripts/protect_branches.py check --repo OWNER/REPO       # 원격 룰셋이 약화·우회되면 실패
```

PR 작성자는 자기 PR을 승인할 수 없으므로 기본값(승인 1)에서는 작성자와 다른 승인 계정이 있어야 병합할 수 있다. 1인 저장소는 `--approvals 0`으로 PR·상태 검사만 강제한다. 이때 GitHub의 리뷰 강제는 사라지지만 구현 시작 gate는 approver의 직접 병합과 병합 후 `implement` 댓글을 계속 요구한다. 룰셋을 풀려면 GitHub 설정에서 소유자가 직접 수정해야 하며 check가 이를 감지한다.

Git flow CI는 신뢰된 base의 스크립트를 실행하고 PR head 코드를 실행하지 않는다. 승인 PR, 요청 댓글, 브랜치, 모든 커밋 참조를 검사한다. 검증 후 승인 취소나 댓글 수정처럼 PR 이벤트를 발생시키지 않는 변경은 자동 재실행되지 않으므로 병합 직전 최신 gate를 재실행한다. 의미적인 범위 준수와 테스트 충실도는 사람 리뷰가 필요하다.

이 폴더에는 현재 `.git`과 원격이 없어 훅 설치·브랜치 생성·GitHub 보호 설정은 적용되지 않았다. 정책 파일·검증 코드·CI는 준비된 상태이며 원격 연결과 계정 설정 후 활성화해야 한다. 최초 정책 설치 PR은 소유자가 부트스트랩하고, 이후 정책 변경도 소유자 리뷰 대상으로 유지한다.
