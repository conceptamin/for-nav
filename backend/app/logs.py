"""실행 명령의 로그 설정. Uvicorn 접근 로그는 쿼리 문자열까지 남기므로 끄고 `app.access`를 쓴다."""

from typing import Any

LOG_CONFIG: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "stderr": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stderr",
        },
    },
    "loggers": {
        "uvicorn": {"handlers": ["stderr"], "level": "INFO", "propagate": False},
        "uvicorn.access": {"handlers": [], "level": "CRITICAL", "propagate": False},
        "app": {"handlers": ["stderr"], "level": "INFO", "propagate": False},
    },
}
