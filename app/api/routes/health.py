"""GET /health endpoint."""
from fastapi import APIRouter

from app.schemas.response import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Readiness probe for the judging harness."""
    return HealthResponse(status="ok")