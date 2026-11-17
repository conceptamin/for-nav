# 33. 센터 로그인 코드 확인을 한 번에 처리하기

상태: 완료
의존: 17

## 목표
`verify_code`(`app/auth.py`)는 `store.get_code` → 비교 → `store.add_code_attempt`를 각각 따로 잠근다. `/api/auth/verify`는 동기 경로라 스레드 풀에서 동시에 돌 수 있고, 동시에 들어온 요청은 모두 "시도 0회"인 코드를 읽은 뒤 비교한다. 그래서 코드 하나에 `CODE_MAX_ATTEMPTS`(5)회보다 훨씬 많이 맞춰 볼 수 있다(6자리 코드라 확률은 낮지만 상한이 지켜지지 않는다). 확인 전체를 저장소의 잠금·트랜잭션 하나 안에서 하고, 시도 수를 **비교 전에** 올려 동시 요청 수와 상관없이 비교가 5회를 넘지 않게 한다.

## 범위
- 하는 것
  - `CenterStore`에 `check_code(email, code_hash, now) -> bool`을 더한다. 한 잠금(SQLite는 한 트랜잭션) 안에서 차례로:
    1. 코드가 없으면 `False`
    2. 만료됐으면 지우고 `False`
    3. `attempts`를 1 올린다. 올린 값이 `CODE_MAX_ATTEMPTS`를 넘으면 지우고 `False`
    4. `secrets.compare_digest`로 비교한다. 맞으면 지우고 `True`, 틀리면 `False`(5번째로 틀렸으면 지운다)
  - `MemoryStore`와 `SqliteStore` 둘 다 구현한다
  - `verify_code`는 `check_code`만 부르고, 맞았을 때 직원 여부 확인과 세션 만들기는 지금과 같다
  - 더 쓰지 않게 된 `get_code`·`add_code_attempt`는 지운다(다른 곳에서 쓰지 않는지 확인)
- 하지 않는 것
  - API·응답 변경. 틀림·만료·없음은 지금처럼 모두 `401`이다
  - 이메일별 발송 제한이 공격자 요청까지 세는 문제(아래 메모), 만료 세션 행 정리, 로그아웃 뒤 열린 WebSocket 닫기

## API·파일
API 변경 없음.

- `app/store.py`: `CenterStore.check_code`, `MemoryStore.check_code`
- `app/store_sqlite.py`: `SqliteStore.check_code`(`with self._lock, self._db:` 하나 안에서 처리)
- `app/auth.py`: `verify_code`
- 테스트: `tests/test_auth.py`(두 저장소에 같은 경우를 돌리는 기존 방식대로)

## 완료 기준
- [x] `uv run ruff check . && uv run ruff format --check .` 통과, `uv run pytest` 통과. 기존 `test_auth.py`는 고치지 않고 통과한다(지운 저장소 메서드를 직접 부르는 테스트만 `check_code`로 바꾼다)
- [x] 동시성: 두 저장소 각각에서 스레드 20개가 틀린 코드로 동시에 `verify_code`를 부르면, 비교가 일어난 횟수(가짜 `compare_digest` 또는 저장소 호출 기록으로 센다)가 5 이하이고, 그 뒤 맞는 코드도 `None`이다
- [x] 순서: 틀린 코드 4번 → 맞는 코드는 통과. 틀린 코드 5번 → 맞는 코드도 거절
- [x] 만료된 코드는 시도 수와 상관없이 거절되고 지워진다

## 결과
- `uv run ruff check . && uv run ruff format --check .` → All checks passed, 97 files already formatted
- `uv run pytest` → 3070 passed(새 테스트 8개: `test_auth.py` 4개 × 두 저장소). 기존 `test_auth.py`는 고치지 않고 통과
- 동시성 테스트가 경쟁을 잡는지 확인: 같은 테스트를 옛 코드(`origin/main`)에 붙여 돌리면 두 저장소 모두 `assert 20 <= 5`로 실패한다(스레드 20개가 모두 비교). 새 코드는 5 이하로 통과. 비교 횟수는 `secrets.compare_digest`를 세는 가짜(비교마다 2ms 대기로 끼어들 틈을 넓힘)로 센다
- API 변경 없음. 틀림·만료·없음은 그대로 모두 `401`
- 파일: `app/store.py`(`CenterStore.check_code`, `MemoryStore.check_code`, `CODE_MAX_ATTEMPTS`를 여기로 옮김), `app/store_sqlite.py`(`SqliteStore.check_code`), `app/auth.py`(`verify_code`), `README.md`(로그인 절 한 줄), 테스트 `tests/test_auth.py`·`tests/test_store.py`
- 결정
  - `CODE_MAX_ATTEMPTS`는 `app/auth.py`에서 `app/store.py`로 옮겼다. 저장소가 한 잠금 안에서 상한을 지켜야 하는데 `auth.py`가 `store.py`를 불러 순환 참조가 되기 때문이다. 시그니처는 문서대로 `check_code(email, code_hash, now) -> bool`
  - `get_code`·`add_code_attempt`에 더해 `delete_code`도 지웠다. `verify_code`가 쓰지 않게 되자 테스트 말고는 부르는 곳이 없었다(직원 삭제는 자기 SQL로 코드를 지운다). `AuthCode`는 메모리 저장소 안에서만 쓴다
  - `tests/test_store.py`의 `test_code_attempts_and_replace`와 `test_sessions_expire_and_end_with_staff`의 마지막 줄은 지운 메서드 대신 `check_code`로 같은 뜻(새 코드가 이전 코드·시도 수를 덮는다, 한 번 쓰면 지운다, 직원 삭제 때 코드도 지운다)을 확인한다

## 메모
- 출처: 2026-11-16 코드 리뷰
- 같은 리뷰에서 나온 관련 일(따로 항목으로): `check_rate`(`app/auth.py`)의 이메일별 발송 제한은 누가 요청했는지 구분하지 않는다. 직원 이메일을 아는 사람이 60초마다 `/api/auth/code`를 부르면 직원은 `429`를 받고 코드도 계속 바뀐다. IP별 제한을 더하거나, 이미 유효한 코드가 있으면 새로 만들지 않고 다시 보내는 방식을 검토한다
