from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def get_health() -> dict[str, str]:
    # 생존 확인 전용이다. DB·파일·네트워크·환경 변수를 읽지 않는다.
    # 응답 스키마는 계약 phase에서 확정한다.
    return {"status": "ok"}
