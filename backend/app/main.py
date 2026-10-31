# 울산 외국인 의료 내비게이터 목업 서버.
# 프론트 브라우저 안의 규칙·템플릿·mock을 같은 입력이면 같은 결과가 나오도록 옮겼다.
# LLM(추출·템플릿 슬롯·번역)과 응급도·진료과 모델은 설정이 있을 때만 붙고, 없으면 규칙·템플릿으로 동작한다.

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import errors
from app.chat import CallHub, ChatHub
from app.llm_limit import LLMLimiter
from app.mail import make_mailer
from app.model import load_model
from app.routers import auth, center, worker
from app.schemas import Meta
from app.settings import get_llm_client, settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # LLM 클라이언트는 시작 시 한 번 만들고 종료 시 닫는다. 키가 없으면 None이고 LLM 자리는 규칙·템플릿으로 동작한다.
    app.state.llm = get_llm_client()
    # 모델은 MODEL_DIR이 있을 때만 시작 시 한 번 읽는다. 아티팩트가 깨졌으면 여기서 실패해 서버가 뜨지 않는다.
    app.state.model = load_model(settings.model_dir)
    try:
        yield
    finally:
        if app.state.llm is not None:
            await app.state.llm.aclose()


app = FastAPI(title="Ulsan Medical Navigator mock API", version="0.1.0", lifespan=lifespan)
# 상담 채팅의 열린 연결(backlog 14). 닫을 것이 없어 lifespan 밖에서 만든다. 테스트가 TestClient를 `with` 없이 써도 있어야 한다.
app.state.chat = ChatHub()
# 통화의 열린 연결(backlog 16). 채팅과 같은 이유로 여기서 만든다.
app.state.call = CallHub()
# LLM 호출 제한(backlog 20). 설정값이 0이면 꺼져 있고 LLM 클라이언트를 감싸지 않는다.
app.state.llm_limiter = LLMLimiter(settings.llm_rate_per_min, settings.llm_daily_limit, settings.llm_client_ip_header)
# 센터 직원 로그인 코드 메일(backlog 17). CENTER_AUTH=off이면 None이다. 테스트는 가짜로 바꿔 끼운다.
app.state.mail = make_mailer(settings)

errors.install(app)
# 프론트는 Vite 프록시로 같은 출처에서 부른다. 개발 중 직접 호출에 대비해 허용 출처(CORS_ORIGINS, 기본 프론트 개발 서버)만 연다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[errors.REQUEST_ID_HEADER],
)


@app.get("/api/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/api/meta")
def meta() -> Meta:
    """S-08·S-12: 정보 기준일과 센터 운영 시간."""
    return Meta(info_date=settings.info_date, center_hours=settings.center_hours)


app.include_router(worker.router, prefix="/api", tags=["worker"])
app.include_router(center.router, prefix="/api", tags=["center"])
app.include_router(auth.router, prefix="/api", tags=["auth"])


def mount_frontend(app: FastAPI, static_dir: str) -> None:
    """프론트 빌드(frontend/dist)를 같은 출처에서 서빙한다(backlog 08). 위 /api 경로보다 뒤에 붙여야 한다.

    있는 파일은 그대로, 나머지 경로는 index.html(SPA 라우팅)이다. /api 아래 없는 경로는 지금처럼 JSON 404다.
    """
    root = Path(static_dir).resolve()
    index = root / "index.html"

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise StarletteHTTPException(status_code=404)
        file = (root / path).resolve()
        # ../ 로 폴더 밖 파일을 읽지 못하게 root 안의 파일만 돌려준다.
        if path and file.is_relative_to(root) and file.is_file():
            return FileResponse(file)
        # 없는 /assets/x.js에 HTML을 주면 브라우저 오류가 헷갈리므로, 확장자가 있는 경로는 404다.
        if Path(path).suffix:
            raise StarletteHTTPException(status_code=404)
        return FileResponse(index)


if settings.static_dir:
    mount_frontend(app, settings.static_dir)
