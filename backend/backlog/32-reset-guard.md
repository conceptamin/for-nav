# 32. 운영 DB에서 데모 초기화(`/reset`) 막기

상태: 대기
의존: 없음

## 목표
`POST /api/center/reset`은 live 사례·상태 변경·채팅·자막·푸시 기기 묶음을 확인이나 백업 없이 지운다(`app/store_sqlite.py` `reset`). 센터 화면의 초기화 버튼은 공개 체험 동안 `CENTER_AUTH=off`라서 `disabled`로 막아 두었지만(`frontend/src/pages/center/Center.tsx` C-01 정렬 옆 주석), 서버 경로는 열려 있다. `CENTER_AUTH=off`이면 `staff_only` 의존성이 그냥 통과하므로 누구나 `curl` 한 번으로 운영 데이터를 지울 수 있다. 운영 저장소(`DB_PATH` 있음)에서는 명시적으로 켰을 때만 이 경로가 동작하게 하고, 켰을 때도 지우기 전에 백업을 남긴다.

## 범위
- 하는 것
  - 설정 `ALLOW_RESET`(`true` | `false`). **`DB_PATH`가 없으면(메모리 저장소: 로컬 개발·테스트) 지금처럼 늘 허용**하고, `DB_PATH`가 있으면 `ALLOW_RESET=true`일 때만 허용한다. 기존 테스트는 메모리 저장소라 바뀌지 않는다
  - 허용되지 않으면 `POST /api/center/reset`은 `404`(경로가 없는 것처럼). 저장소·채팅·통화 허브를 건드리지 않는다
  - 허용되고 저장소가 SQLite면, 지우기 전에 `sqlite3.Connection.backup`으로 `<DB_PATH>.reset-<UTC 시각>.bak`를 같은 폴더에 쓴다. 백업이 실패하면 지우지 않고 `500`이다
  - 막을 때 로그 한 줄 `center reset blocked`(요청 IP·본문은 남기지 않는다)
- 하지 않는 것
  - 맥미니 `ecosystem.config.cjs`에 `ALLOW_RESET`을 넣는 것. 운영은 기본으로 막힌다
  - 백업 파일 보존 개수 관리·자동 삭제(초기화가 드물다. 필요하면 메모로 남긴다)
  - 프론트 버튼 변경. 버튼은 그대로 `disabled`다. 다시 쓰려면 `frontend/` 브랜치에서 따로 한다
  - `CENTER_AUTH` 기본값 변경(별도 항목. 아래 메모)

## API·파일
- `POST /api/center/reset`: `DB_PATH`가 있고 `ALLOW_RESET`이 꺼져 있으면 `404 NOT_FOUND`. 그 밖에는 지금과 같다(`204`)
- `app/settings.py`: `allow_reset: bool = False`, `_bool("ALLOW_RESET", …)`
- `app/routers/center.py` `reset`: 허용 여부 확인 → 백업 → `store.reset()`
- `app/store.py`·`app/store_sqlite.py`: `CenterStore`에 `backup(path) -> None`(메모리 구현은 아무 일도 하지 않는다)
- `.env.example`, `README.md`(API 표의 `/reset` 행, "센터 저장소" 절에 조건 한 줄)
- 테스트: `tests/test_api.py` 또는 `tests/test_store.py`, `tests/test_settings.py`

## 완료 기준
- [ ] `uv run ruff check . && uv run ruff format --check .` 통과, `uv run pytest` 통과. 기존 reset 테스트(`test_api.py`, `test_call.py`)는 고치지 않고 통과한다
- [ ] `DB_PATH`=임시 파일, `ALLOW_RESET` 없음 → `POST /api/center/reset`이 `404`이고 live 사례·채팅이 그대로다
- [ ] `DB_PATH`=임시 파일, `ALLOW_RESET=true` → `204`, 같은 폴더에 `.reset-*.bak`가 생기고 그 파일을 열면 지우기 전 live 사례 수가 그대로다
- [ ] 백업이 실패하도록 만든 경우(쓸 수 없는 폴더) → `500`이고 데이터가 지워지지 않는다
- [ ] `ALLOW_RESET`이 `true`·`false`가 아닌 값이면 서버가 뜨지 않는다

## 결과
(구현 후 작성)

## 메모
- 출처: 2026-11-16 코드 리뷰. 운영 `.env`의 `CENTER_AUTH` 값은 서버에 요청해 확인하지 않았다. 프론트 주석대로 `off`라면 이 항목이 가장 급하다
- 같은 리뷰에서 나온 관련 일: `CENTER_AUTH`가 `.env`에서 빠지면 센터 경로 전체가 열린다(기본값 `off`, `deploy/ecosystem.config.cjs`가 강제하지 않음). 공개 체험이 끝나면 `ecosystem.config.cjs`에 `CENTER_AUTH=email`을 고정하는 항목을 따로 만든다
