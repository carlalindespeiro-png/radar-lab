from fastapi import APIRouter
from app.api import health as health_module
from app.api.v1 import sectors, territories
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_module.router)
api_router.include_router(sectors.router)
api_router.include_router(territories.router)