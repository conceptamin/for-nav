from fastapi import FastAPI

from app.api.router import api_router


def create_app() -> FastAPI:
    # Swagger UI·ReDoc은 외부 CDN 자산을 불러오므로 제공하지 않는다.
    app = FastAPI(title="for-nav API", docs_url=None, redoc_url=None)
    app.include_router(api_router)
    return app
