# 울산 외국인 의료 내비게이터 목업 서버.
# 프론트 브라우저 안의 규칙·템플릿·mock을 같은 입력이면 같은 결과가 나오도록 옮겼다. LLM·학습 모델은 아직 붙이지 않는다.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import errors
from app.routers import center, worker
from app.schemas import Meta
from app.settings import settings

app = FastAPI(title="Ulsan Medical Navigator mock API", version="0.1.0")

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
