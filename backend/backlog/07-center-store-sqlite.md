# 07. 센터 저장소를 SQLite로 교체

상태: 완료
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
- [x] `uv run pytest` 통과. `test_api.py`의 센터 경로 테스트가 두 구현 모두에서 통과한다
- [x] `DB_PATH=./center.db`로 띄워 `POST /api/center/cases` → 서버 재시작 → `GET /api/center/cases`에 그 사례가 있고, `PATCH`로 바꾼 상태도 남아 있다(명령과 결과를 `## 결과`에)
- [x] `POST /api/center/reset` 뒤 live 사례와 상태 변경이 없고 mock 24건은 처음 상태다
- [x] `git status`에 `.db` 파일이 나타나지 않는다

## 결과

### 결정
- `store.py`: `CenterStore`를 `Protocol`로 바꾸고 기존 구현은 `MemoryStore`로 이름을 바꿨다. `open_store(settings.db_path)`가 둘 중 하나를 골라 모듈 변수 `store`에 둔다. 라우터는 그대로 `from app.store import store`다.
- 두 구현이 같은 규칙을 쓰도록 id 만들기(`next_case_id`), 최신순 정렬(`latest_first`), 상태 덮어쓰기(`with_status`)를 `store.py` 함수로 뺐다.
- SQLite: 연결 하나 + 잠금(`check_same_thread=False`). FastAPI 동기 경로가 스레드 풀에서 돌기 때문이다. 쓰기마다 커밋한다. 같은 접수 시각의 live 사례는 `rowid` 역순으로 읽어 메모리 구현(`insert(0)`)과 순서를 맞췄다.
- 상태 변경은 mock·live 모두 `case_status`에 둔다. mock id는 시드 고정이라 재시작해도 같다.
- `DB_PATH`는 폴더가 있는지만 시작 시 확인한다(파일은 처음 열 때 만든다).
- `close()`는 프로토콜에 두었지만 서버 lifespan에서는 부르지 않는다. 저장소가 모듈 변수라 테스트가 `TestClient(app)`를 여러 번 열고 닫기 때문이고, 쓰기마다 커밋하므로 종료 시 잃는 것이 없다.

### 실행
- `uv run ruff check . && uv run ruff format --check .` → 통과
- `uv run pytest` → 2792 passed. 새 `tests/test_store.py` 14개(메모리·SQLite 각 5개 + SQLite 재시작·파일 유지·저장소 고르기·`DB_PATH` 검사 4개). `tests/test_api.py`의 센터 경로 테스트 9개를 `center_store` 픽스처로 두 구현에 돌린다(+9)
- 실제 서버 재시작 확인(`DB_PATH=./center.db uv run fastapi run app/main.py --port 8766`, curl)

| 단계 | 결과 |
|---|---|
| 1. `POST /api/center/cases` | `C-65486` 생성 |
| 2. `PATCH C-65486 {status: progress}`, `PATCH C-1024 {status: done}` | `progress`, `done` |
| 3. 서버 종료 → 다시 시작 | |
| 4. `GET /api/center/cases` | 25건, `C-65486` `live: true` `status: progress`, `C-1024` `status: done` |
| 5. `POST /api/center/reset` | 204 |
| 6. `GET /api/center/cases` | 24건, live 0건, `new`가 아닌 상태 18건(새 메모리 저장소의 mock 시드와 같은 18건) |
| 7. 파일 | `center.db` 그대로(20KB) |

- `git status` → `center.db`가 나타나지 않는다(`.gitignore`의 `*.db`, `*.db-*`). 확인 뒤 파일은 지웠다

### 바뀐 API
- 없음. `DB_PATH`가 있을 때만 재시작 뒤에도 사례·상태가 남는다

### 남은 문제
- 연락처·자유 입력이 평문으로 파일에 남는다(README에 적음). 보존 기간·삭제·암호화는 PRD 미결
- 서버 프로세스 하나만 가정한다(`fastapi run --workers 1`). 여러 프로세스가 같은 파일을 쓰는 경우는 범위 밖

## 메모
- 연락처·자유 입력이 평문으로 파일에 남는다. 데모 범위에서는 허용하되 `README.md`에 적는다
- 보존 기간과 삭제 규칙은 PRD 미결이다. 정해지면 별도 항목으로 만든다
- 사례 id 충돌 처리(`-2`, `-3`)는 표의 기본 키로 보장되므로 SQLite 구현에서도 같은 규칙을 유지한다
