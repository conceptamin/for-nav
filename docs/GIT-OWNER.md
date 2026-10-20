# 소유자 운영 문서

`.github/git-flow.json`의 approver(프로젝트 소유자)만 다루는 설정과 규칙이다. 모든 참여자가 따르는 흐름은 [Git Flow](GIT-FLOW.md)에 있다.

## approver와 저장소 설정

`.github/git-flow.json`에 실제 `repository` (`owner/repo`)와 승인자의 GitHub `approver` 로그인명을 입력한다. 값을 추정하거나 AI가 임의로 승인자로 등록하지 않는다. 값이 비면 구현 시작이 의도적으로 차단된다. approver는 백로그 PR을 승인·병합하고, 정책 PR을 직접 제출하며, 원격 보호를 적용한다.

GitHub 저장소 Settings → General → Pull Requests에서 **Automatically delete head branches**를 켠다. 병합된 작업 브랜치가 원격에서 자동으로 지워지므로 참여자는 로컬 정리(`scripts/cleanup_branches.py`)만 하면 된다. 병합 방식 체크박스는 그대로 두어도 아래 룰셋이 브랜치별로 제한한다.

## PR 리뷰와 병합

병합은 승인자만 한다. 병합 방식은 항상 **Squash and merge**다. 자동 검사(approval-gate·harness)는 형식만 확인하므로 범위와 품질은 아래 항목으로 직접 본다.

**백로그 PR** (`backlog/` → develop)

- phase 문서 하나만 바뀌었는가. 목표·범위·제외 범위·선행 작업·수용 기준·검증 방법이 채워졌는가.
- 선행 phase의 완료 증거가 있는가. 공유 계약을 바꾼다면 결정 근거와 fixture·소비자 갱신 계획이 있는가.
- 최신 커밋을 기준으로 승인한다. 직접 병합하면 승인으로 인정된다. 다른 사람이 승인자 리뷰 없이 병합하면 이후 구현 시작(`start`)이 승인 없음으로 차단된다.
- 병합 뒤 문서를 다시 바꾸면 재승인이 필요하다.

**구현 PR** (`feature/` → develop)

- 본문의 Backlog·Approval-PR·Request-Comment·Backlog-Revision이 승인한 백로그와 같은가. approval-gate가 통과했는가.
- 변경이 승인된 범위 안에 있는가. phase 문서의 목표·범위·수용 기준이 바뀌지 않았는가.
- 완료 조건마다 실행한 명령과 결과가 phase 문서에 있는가. `Not-tested` 항목과 남은 위험을 받아들일 수 있는가.
- 루트 `CLAUDE.md`의 불변식(서버가 통행 상태의 원본, 시간 만료는 해제 증거가 아님 등)을 어기지 않는가.

**정책 PR** (`policy/` → develop): 승인자가 직접 제출한다. 제품 gate를 완화하지 않는지 본다.

**병합 권한의 서버 강제**: 현재 룰셋은 승인 0(`--approvals 0`)이라 쓰기 권한이 있는 참여자는 누구나 병합 버튼을 누를 수 있다. 지금은 collaborator가 승인자 한 명뿐이라 문제가 없다. 팀원을 추가하기 전에 별도 정책 PR로 강제 방식을 정한다. 단순히 승인 1과 CODEOWNERS를 켜면 승인자가 자기 PR(정책 PR 등)을 스스로 승인할 수 없어 병합이 막힌다.

## 정책 브랜치

정책 브랜치(`policy/<slug>`)는 하네스와 운영 규칙(`.github/`, `.githooks/`, `.gitignore`, `CLAUDE.md`, `README.md`, 영역별 `AGENTS.md`, `docs/`, `scripts/`, `tests/harness/`)만 바꾼다. 제품 코드·`backlog/`·`fixtures/`·`shipyard-*.md` 기획·계약서는 포함할 수 없고 파일 이동으로도 옮길 수 없다. 계약 변경은 phase 문서에서 fixture·소비자와 함께 다룬다. AI가 초안과 커밋을 작성할 수 있지만 PR은 approver가 직접 제출한다. approval-gate는 PR 작성자가 approver인지 확인하며, 하네스 유지보수 요청은 제품 구현 승인이 아니다. 정책 PR의 gate도 base(develop)의 스크립트로 실행되므로 정책 PR이 자기 검사를 완화해 통과할 수 없다. policy 경로를 처음 도입하는 변경은 base에 아직 규칙이 없으므로 룰셋 적용 전에 소유자가 부트스트랩한다.

## 원격 보호

원격 저장소에서 main/develop에 필수 PR, 필수 승인, stale approval 무효화, 마지막 push 재승인, force push/삭제 금지, 우회 권한 제한, 병합 방식 고정을 적용한다. 백로그와 정책 파일에는 소유자의 CODEOWNERS 승인을 필수로 설정한다. 필수 상태 검사는 `Git flow / approval-gate` 및 `Backlog harness / harness`로 지정한다. 실제 UI의 check 이름을 확인한다. 소유자 로그인 확정 전 가짜 CODEOWNERS 항목은 생성하지 않는다.

위 보호는 `scripts/protect_branches.py`가 브랜치별 GitHub 룰셋 `yardpilot-protected-develop`·`yardpilot-protected-main`으로 적용한다. 룰셋은 우회 주체가 없어 관리자도 main/develop에 직접 push·삭제·force push할 수 없고, `approval-gate`가 feature→develop·backlog→develop·policy→develop·release→main/develop 외의 병합을 막는다. 상태 검사는 GitHub Actions(integration 15368) 결과만 인정한다. develop은 squash 병합만, main은 merge commit만 허용한다. main까지 squash하면 release 병합 커밋이 develop 이력에 없어 다음 release에서 충돌한다. check는 병합 방식 목록이 정확히 일치하는지 비교하므로 서버 기본값(세 방식 모두 허용)으로 돌아가면 실패한다. apply는 저장소 관리자 권한이 필요하며 소유자가 직접 실행한다. AI는 plan·check만 실행한다.

| 명령 | 하는 일 |
|---|---|
| `python3 scripts/protect_branches.py plan --approvals 0` | 적용할 룰셋 출력, 네트워크 없음 |
| `python3 scripts/protect_branches.py apply --approvals 0` | 소유자만: 브랜치별 룰셋 생성·갱신, 구 룰셋 삭제 |
| `python3 scripts/protect_branches.py check --approvals 0` | 원격 룰셋이 약화·우회되면 실패 |

`--repo`를 생략하면 `.github/git-flow.json`의 repository를 쓴다. 이 저장소는 1인 저장소라 `--approvals 0`으로 적용돼 있으므로 check도 같은 값으로 실행한다. PR 작성자는 자기 PR을 승인할 수 없으므로 기본값(승인 1)에서는 작성자와 다른 승인 계정이 있어야 병합할 수 있다. `--approvals 0`이면 GitHub의 리뷰 강제는 사라지지만 구현 시작 gate는 approver의 직접 병합과 병합 후 `implement` 댓글을 계속 요구한다. 룰셋을 풀려면 GitHub 설정에서 소유자가 직접 수정해야 하며 check가 이를 감지한다.

이전 공용 룰셋 `yardpilot-protected-branches`는 병합 방식을 고정하지 않는다. 브랜치별 룰셋을 도입하는 정책 PR이 병합되면 소유자가 develop에서 `apply --approvals 0`을 한 번 실행한다. apply는 새 룰셋을 먼저 만든 뒤 구 룰셋을 지워 보호가 비는 순간이 없게 한다. 구 룰셋이 남아 있는 동안 check는 실패한다.

## CI의 한계

로컬 훅과 AI 자격 증명의 한계는 [Git Flow](GIT-FLOW.md#강제력과-원격-보호)에 있다. Git flow CI는 신뢰된 base의 스크립트를 실행하고 PR head 코드를 실행하지 않는다. 승인 PR, 요청 댓글, 브랜치, 모든 커밋 참조를 검사한다. 검증 후 승인 취소나 댓글 수정처럼 PR 이벤트를 발생시키지 않는 변경은 자동 재실행되지 않으므로 병합 직전 최신 gate를 재실행한다. 의미적인 범위 준수와 테스트 충실도는 사람 리뷰가 필요하다.

최초 정책 설치 PR은 소유자가 부트스트랩했고 이후 정책 변경도 소유자 리뷰 대상으로 유지한다.
