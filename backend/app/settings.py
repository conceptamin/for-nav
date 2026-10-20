"""실행 설정. 환경 변수에서 읽으며 앱 응답에는 노출하지 않는다."""

import os
from collections.abc import Mapping
from dataclasses import dataclass

HOST_ENV = "YARDPILOT_API_HOST"
PORT_ENV = "YARDPILOT_API_PORT"
# 프론트 dev proxy 기본값 YARDPILOT_API_ORIGIN=http://127.0.0.1:8000과 맞춘다.
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


@dataclass(frozen=True)
class Settings:
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT


def load_settings(environ: Mapping[str, str] = os.environ) -> Settings:
    host = environ.get(HOST_ENV, DEFAULT_HOST).strip()
    if not host:
        raise ValueError(f"{HOST_ENV}가 비어 있습니다")
    raw_port = environ.get(PORT_ENV, str(DEFAULT_PORT)).strip()
    if not raw_port.isdigit() or not 1 <= int(raw_port) <= 65535:
        raise ValueError(f"{PORT_ENV}는 1~65535 정수여야 합니다: {raw_port!r}")
    return Settings(host=host, port=int(raw_port))
