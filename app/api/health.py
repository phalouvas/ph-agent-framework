from fastapi import APIRouter

from app.schemas.common import HealthResponse

router = APIRouter()

APP_VERSION = "1.0.0"


@router.get("/health", response_model=HealthResponse, summary="Health check")
async def health():
    """Check if the service is running and healthy."""
    return HealthResponse(status="ok", version=APP_VERSION)
