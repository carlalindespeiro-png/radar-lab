from fastapi import APIRouter
from app.shared.schemas import HealthResponse
router = APIRouter(tags=["health"])
@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse: return HealthResponse(status="healthy", version="0.1.0")