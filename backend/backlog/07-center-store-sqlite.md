# 07. 센터 저장소를 SQLite로 교체

상태: 대기
의존: 01

## 목표
센터 접수함이 서버 재시작 뒤에도 남도록 메모리 저장소를 SQLite 파일로 바꾼다. `CenterStore` 인터페이스와 mock 시드, 데모 초기화 동작은 그대로 두어 라우터와 테스트가 바뀌지 않게 한다.

## 범위
- 하는 것
  - `app/settings.py`에 `DB_PATH`(기본 빈 값 = 지금 메모리 저장소) 추가
  - `app/store_sqlite.py`: 표준 라이브러리 `sqlite3`만 쓴다. 표는 `live_cases`(id, created_at, 본문 JSON), `case_status`(id, status). mock 사례는 지금처럼 시작 시 메모리에서 만들고 상태만 표에 둔다
  - `store.py`의 `CenterStore`를 프로토콜로 바꾸고 `DB_PATH` 유무로 둘 중 하나를 고른다
  - `reset()`은 두 표를 비운다. 파일은 지우지 않는다
  - `tests/test_store.py`: 같은 테스트를 메모리·SQLite 두 구현에 돌린다(임시 파일). 재시작 흉내: 저장소를 두 번 만들어 live 사례와 상태가 남는지
  - `.gitignore`에 `*.db`, `*.db-*`
- 하지 않는 것
  - ORM·마이그레이션 도구, 다중 프로세스 동시 쓰기, 보존 기간·자동 삭제, 암호화, 통계 레코드 저장(mock 그대로)

## API·파일
- 변경되는 API 없음
- 추가: `app/store_sqlite.py`, `tests/test_store.py`
- 수정: `app/store.py`, `app/settings.py`, `.env.example`, `.gitignore`, `README.md`(기술 스택 표 "저장소" 행, 환경 변수 표)

## 완료 기준
- [ ] `uv run pytest` 통과. `test_api.py`의 센터 경로 테스트가 두 구현 모두에서 통과한다
- [ ] `DB_PATH=./center.db`로 띄워 `POST /api/center/cases` → 서버 재시작 → `GET /api/center/cases`에 그 사례가 있고, `PATCH`로 바꾼 상태도 남아 있다(명령과 결과를 `## 결과`에)
- [ ] `POST /api/center/reset` 뒤 live 사례와 상태 변경이 없고 mock 24건은 처음 상태다
- [ ] `git status`에 `.db` 파일이 나타나지 않는다

## 결과

## 메모
- 연락처·자유 입력이 평문으로 파일에 남는다. 데모 범위에서는 허용하되 `README.md`에 적는다
- 보존 기간과 삭제 규칙은 PRD 미결이다. 정해지면 별도 항목으로 만든다
- 사례 id 충돌 처리(`-2`, `-3`)는 표의 기본 키로 보장되므로 SQLite 구현에서도 같은 규칙을 유지한다
