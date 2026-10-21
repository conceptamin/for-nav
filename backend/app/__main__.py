"""`python -m app`: 단일 worker Uvicorn으로 API 서버를 실행한다."""

import uvicorn

from app.main import create_app
from app.settings import load_settings


def main() -> None:
    try:
        settings = load_settings()
    except ValueError as exc:
        raise SystemExit(f"설정 오류: {exc}") from None
    # backend/AGENTS.md의 단일 worker 실행 규칙에 맞춰 worker 수와 reload를 고정한다.
    uvicorn.run(create_app(), host=settings.host, port=settings.port, workers=1, reload=False)


if __name__ == "__main__":
    main()
