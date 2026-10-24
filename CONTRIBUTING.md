# 작업 약속

복잡한 절차 없이 아래만 지킨다. 브랜치·커밋·PR 형식은 [Git 컨벤션](docs/git-convention.md)에 있다.

## 1. main은 PR로만 바꾼다

- main에 직접 커밋·push하지 않는다. 로컬 훅과 GitHub 룰셋이 둘 다 막는다.
- 작업은 브랜치에서 하고 PR을 연다. CI(`frontend`·`backend`)가 통과해야 병합할 수 있다(룰셋이 강제).
- 다른 사람에게 리뷰·승인을 받고 병합하는 것을 약속으로 한다. 룰셋은 승인 수를 강제하지 않는다(필요 승인 0명). GitHub은 작성자가 자기 PR을 승인하지 못하므로 혼자 맡은 작업은 소유자가 승인 없이 병합할 수 있게 두었다. 미해결 리뷰 대화가 있으면 병합되지 않는다.
- 브랜치 이름은 `<영역>/<내용>` 형식으로 쓴다. 예: `frontend/summary-card`, `backend/route-rules`, `modeling/baseline`, `docs/api-contract`.

## 2. 폴더를 지킨다

| 폴더 | 무엇 | 담당 |
|---|---|---|
| `frontend/` | 모바일 웹 화면. 문서는 `frontend/docs/` | 화면 |
| `backend/` | API, 비용 경로·진료과 규칙, LLM 호출, 병원 데이터. 문서는 `backend/docs/` | 서버·LLM |
| `modeling/` | 응급 감지 모델, 학습 데이터, 테스트셋, 평가. 문서는 `modeling/docs/` | 모델링 |
| `docs/` | 세 영역이 같이 보는 문서(공통 API 계약, Git 컨벤션) | 전원 |
| `fixtures/` | 계약 예시 JSON, 비용 경로 정답 사례 | 콘텐츠·발표 (정답 사례) |

- 내 영역 밖 폴더를 고쳐야 하면 PR에 적고 그 영역 담당에게 리뷰를 받는다.
- 공통 계약(`docs/api-contract.md`)을 바꾸면 `fixtures/`와 쓰는 쪽 코드를 같은 PR에서 함께 고친다.
- 비용 경로 정답(`fixtures/route-cases/`)은 규칙을 만들지 않은 사람이 쓴다. 규칙 담당은 정답을 고치지 않는다.
- 최종 테스트셋(`modeling/data/test/`)은 10월 22일에 고정한 뒤 학습·조정에 쓰지 않는다.

## 3. phase 문서

- 각 영역의 `docs/phase-XX.md`에 쓴다. 번호는 영역마다 따로 매긴다.
- 들어갈 내용: 목표, 범위(포함·제외), 할 일 체크리스트, 완료 기준, 검증 결과.
- 다른 영역에 의존하면 그 문서 경로를 적는다. 예: `../../backend/docs/phase-02.md`
- 구현이 끝나면 실행한 테스트와 결과를 같은 문서에 남긴다.
- `phase-01.md`는 이전 프로젝트(YardPilot)에서 만든 실행·검증 기반의 기록이다. 코드가 그대로 남아 있어 지우지 않는다.

## 4. 테스트

- PR을 올리기 전에 내 영역 테스트를 돌린다. 명령은 각 영역의 `AGENTS.md`에 있다.
- CI가 PR마다 프론트·백엔드 테스트를 자동으로 돌린다. 실패하면 병합할 수 없다. 모델링 CI는 모델링 phase-01에서 붙인다.
- 테스트는 외부 LLM·외부 API를 호출하지 않는다. 가짜 구현으로 대신한다.

## 처음 한 번

```sh
git clone <저장소 URL>
cd for-nav
git config core.hooksPath .githooks
```

마지막 줄이 main 직접 커밋·push를 막는 로컬 훅을 켠다. 저장소 이름이 yardpilot일 때 받아 둔 사람은 `git remote set-url origin <새 URL>`로 주소를 바꾼다.

## 매번 하는 일

```sh
git switch main
git pull
git switch -c <영역>/<내용>
# 작업하고 테스트
git add <파일>
git commit                       # 제목: 변경 이유 한 줄, 본문: 바꾼 것과 테스트 결과
git push -u origin <영역>/<내용>
gh pr create --base main         # --fill은 PR 템플릿을 건너뛰므로 쓰지 않는다
```

리뷰를 받으면 GitHub에서 **Merge pull request**(merge commit)로 병합한다. 룰셋이 이 방식만 허용한다. 병합된 원격 브랜치는 자동으로 지워진다.

Claude Code에 병합을 요청하면 확인 창 없이 `gh pr merge`와 브랜치 삭제까지 한다. 허용 목록은 `.claude/settings.json`에 있고 저장소를 받은 모두에게 적용된다.
