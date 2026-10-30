"""센터 직원 목록을 관리한다(backlog 17). 맥미니에서 서버와 같은 DB_PATH의 SQLite 파일을 연다. CI에서 돌지 않는다.

    uv run --env-file .env python scripts/staff.py add staff@example.org
    uv run --env-file .env python scripts/staff.py remove staff@example.org
    uv run --env-file .env python scripts/staff.py list

remove는 그 직원의 로그인 코드와 세션도 지운다(바로 로그아웃된다). 서버를 다시 띄울 필요는 없다.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import clock  # noqa: E402
from app.auth import normalize_email, valid_email  # noqa: E402
from app.settings import settings  # noqa: E402
from app.store_sqlite import SqliteStore  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="센터 직원 목록(DB_PATH의 SQLite)")
    parser.add_argument("command", choices=["add", "remove", "list"])
    parser.add_argument("email", nargs="?")
    args = parser.parse_args(argv)

    if not settings.db_path:
        print("DB_PATH가 없다. 서버와 같은 .env로 실행한다(uv run --env-file .env ...)", file=sys.stderr)
        return 2
    store = SqliteStore(settings.db_path)
    try:
        if args.command == "list":
            for email in store.list_staff():
                print(email)
            return 0
        email = normalize_email(args.email or "")
        if not valid_email(email):
            print("이메일 형식이 아니다", file=sys.stderr)
            return 2
        if args.command == "add":
            print("추가했다" if store.add_staff(email, clock.now()) else "이미 있다")
        else:
            print("지웠다(세션도 끝났다)" if store.remove_staff(email) else "없는 이메일이다")
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    sys.exit(main())
