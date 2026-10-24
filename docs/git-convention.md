# Git 컨벤션

브랜치·커밋·PR을 사람과 AI가 같은 형식으로 만든다. 작업 약속 전체는 [CONTRIBUTING.md](../CONTRIBUTING.md), AI 규칙은 [CLAUDE.md](../CLAUDE.md)에 있다.

## 처음 한 번: git hook 켜기

`main`에 직접 커밋·push하는 실수를 막는 hook이 `.githooks/`에 있다. clone한 뒤 한 번만 실행한다.

```sh
git config core.hooksPath .githooks
```

| hook | 막는 것 |
|---|---|
| `pre-commit` | `main` 브랜치에서 커밋 |
| `pre-push` | 원격 `main`으로 push (삭제·강제 push 포함) |

hook은 내 컴퓨터에서만 돈다. GitHub 룰셋(`fornav-protected-main`)이 원격에서 한 번 더 막는다.

| 룰셋 규칙 | 뜻 |
|---|---|
| PR로만 병합, merge commit만 허용 | squash·rebase 병합은 안 된다 |
| CI `frontend`·`backend` 통과 | 테스트가 실패하면 병합 버튼이 막힌다 |
| 최신 `main` 반영 | `main`이 앞서 있으면 브랜치를 갱신해야 병합된다 |
| 리뷰 대화 해결 | 열린 리뷰 대화가 있으면 병합되지 않는다 |
| `main` 삭제·강제 push 금지 | |

## 브랜치

```text
<영역>/<짧은-설명>      예: frontend/summary-card, backend/route-rules, modeling/baseline
```

| 영역 | 언제 |
|---|---|
| `frontend` | `frontend/` 화면·클라이언트·테스트 |
| `backend` | `backend/` API·규칙·LLM 호출 |
| `modeling` | `modeling/` 모델·데이터·평가 |
| `fixtures` | 비용 경로 정답 사례 작성(콘텐츠 담당) |
| `docs` | 공통 계약(`docs/api-contract.md`)과 루트 문서 |
| `chore` | CI, hook, `.github/`, 저장소 설정 |

- 설명은 영어 소문자와 `-`로 짧게 쓴다.
- 여러 영역을 건드리면 주된 영역을 쓴다. 공통 계약을 바꾸는 PR은 `fixtures/`와 쓰는 쪽 코드를 함께 고쳐도 `docs/`로 한다.
- 브랜치 하나에는 한 주제만 담는다. 병합된 브랜치에서 이어서 작업하지 않는다.

## 커밋 메시지

### 형식

```text
<무엇을 위해 무엇을 바꾸는지 한 줄>

- <파일·폴더>: <바꾼 내용>
- <파일·폴더>: <바꾼 내용>

테스트: <실행한 명령> → <결과>
```

- 제목은 **변경 이유**를 한 줄에 쓴다. "~하도록 ~한다", "~할 수 있게 ~를 정한다"처럼 이유와 변경을 함께 담는다.
- 한국어로, 평서형(`~한다`)으로, 끝에 마침표 없이 쓴다.
- `feat:`·`fix:` 같은 type 접두사는 쓰지 않는다. 분류는 브랜치 영역이 맡는다.
- phase 구현 커밋은 제목 앞에 `[<영역>/phase-XX]`를 붙인다.
- 본문에는 바뀐 것을 파일·폴더별로 적고, 마지막에 `테스트:` 줄을 꼭 쓴다. 문서만 바꿨으면 그렇게 적고 한 확인(링크 검사 등)을 쓴다. 돌리지 못한 테스트는 못 했다고 적는다.
- 관련 이슈가 있으면 본문 끝에 `#이슈번호`를 붙인다.
- 커밋 하나에는 한 가지 변경만 담는다. 제목이 한 줄에 안 들어가면 커밋을 나눌 때다.
- AI가 만든 커밋은 맨 끝에 `Co-Authored-By:` 줄을 남긴다.

### 제목 예시

| 피할 제목 | 왜 | 이렇게 |
|---|---|---|
| `fix: 버그 수정` | 무엇을 왜 고쳤는지 없음 | `산재 경로가 건강보험 질문을 건너뛰지 않도록 질문 순서 규칙을 고친다` |
| `계약 업데이트` | 무엇이 바뀌었는지 없음 | `번역 누락을 프론트 한 곳에서 잡도록 서버는 문장 대신 코드값을 보낸다` |
| `phase-02 작업` | 범위·이유 없음 | `[backend/phase-02] 같은 입력에 같은 결과가 나오도록 비용 경로를 순수 함수 규칙으로 구현한다` |

### 예시

```text
[modeling/phase-01] 재현율 기준으로 임계값을 정할 수 있도록 TF-IDF 기준 모델과 검증 평가를 만든다

- modeling/train.py: TF-IDF + 로지스틱 회귀 학습, seed 고정, 가중치를 JSON으로 내보냄
- modeling/eval.py: 검증셋 재현율·정밀도·오탐률을 분자·분모와 출처별로 출력
- modeling/docs/phase-01.md: 버전 출처(PyPI, 2026-10-23)와 검증 결과 기록

테스트: uv run pytest → 14 passed, 같은 seed로 두 번 학습 → 모델 해시 동일
```

### 커밋에 넣지 않는 것

- API 키, `.env` 같은 비밀 값
- `modeling/data/external/` 원본 데이터 (`.gitignore`로 제외)
- 실제 사용자 입력, 이름·연락처·사업장명 같은 식별 정보
- 빌드 산출물(`dist/`), 가상환경(`.venv/`), 캐시

## PR 올리기

브랜치를 push한 뒤 GitHub CLI(`gh`)로 PR을 만든다.

```sh
# 처음 한 번: 설치와 로그인
brew install gh                    # macOS
winget install --id GitHub.cli     # Windows
sudo apt install gh                # Linux/Ubuntu
gh auth login

# PR 만들기
git push -u origin <영역>/<짧은-설명>
gh pr create --base main           # 제목·본문을 묻고, 본문에는 PR 템플릿이 채워진다
gh pr create --base main --web     # 브라우저에서 쓰고 싶을 때

# PR 확인
gh pr status                       # 내 PR 상태
gh pr checks                       # CI 결과
gh pr view --web                   # 현재 브랜치의 PR을 브라우저로 열기
```

- 제목은 커밋 제목과 같은 형식으로 쓴다. 커밋이 하나면 그 제목을 그대로 쓴다.
- 본문은 [PR 템플릿](../.github/pull_request_template.md)의 두 칸을 채운다. **무엇을 왜**에는 관련 phase 문서 경로를, **확인한 것**에는 실행한 테스트와 결과를 쓴다.
- `--fill`은 템플릿 대신 커밋 내용으로 본문을 채우므로 쓰지 않는다.
- PR을 올리기 전에 내 영역 테스트를 돌린다. 명령은 각 영역 `AGENTS.md`에 있다.
- 내 영역 밖 폴더를 고쳤으면 본문에 적고 그 영역 담당에게 리뷰를 요청한다.
- `fixtures/route-cases/` 정답이 틀렸다고 보이면 고치지 말고 PR에 근거를 적어 콘텐츠 담당에게 묻는다.

## 병합

- 다른 사람에게 리뷰를 받은 뒤 GitHub에서 **Merge pull request**로 병합한다. 혼자 맡은 작업은 소유자가 승인 없이 병합할 수 있다.
- 병합 버튼이 막혀 있으면 `gh pr checks`로 CI를, PR 화면에서 열린 리뷰 대화와 "This branch is out-of-date" 표시를 확인한다. 브랜치가 뒤처졌으면 아래 [최신 main 반영하기](#작업-중인-브랜치에-최신-main-반영하기)를 한 뒤 다시 push한다.
- 병합된 원격 브랜치는 자동으로 지워진다. 로컬 브랜치는 직접 지운다.
- AI는 사람이 요청할 때만 병합하고 브랜치를 지운다.

## 최신 버전 받기

### 새 작업 시작

PR이 병합된 뒤 새 작업을 시작할 때는 `main`을 최신으로 받고 새 브랜치를 만든다.

```sh
git switch main
git pull origin main
git switch -c <영역>/<짧은-설명>

# 병합된 로컬 브랜치 정리
git branch -d <병합된-브랜치>
git fetch --prune                  # 지워진 원격 브랜치 목록 정리
```

### 작업 중인 브랜치에 최신 main 반영하기

브랜치를 옮기지 않고 `main`을 merge로 받는다. 이미 push한 브랜치를 rebase하면 강제 push가 필요해지므로 rebase는 쓰지 않는다.

```sh
git pull origin main               # main의 변경을 현재 브랜치에 merge
git push

# 커밋하지 않은 작업이 있어 pull이 막힐 때
git stash                          # 작업 중인 변경을 임시 저장
git pull origin main
git stash pop                      # 작업 내용 되돌리기
```

- 충돌이 나면 해당 파일의 `<<<<<<<` ~ `>>>>>>>` 구간을 정리하고 `git add <파일>` 후 커밋한다.
- `git stash pop`에서 충돌이 나면 stash가 남아 있으므로, 정리한 뒤 `git stash drop`으로 지운다.
- `uv.lock`·`package-lock.json`이 충돌하면 손으로 고치지 말고 한쪽을 받은 뒤 `uv lock`·`npm install`로 다시 만든다.
