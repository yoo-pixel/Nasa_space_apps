from fastapi import APIRouter
from app.api.v1.endpoints.core import router as core_router
from app.api.v1.endpoints.monitoring import router as monitoring_router
from app.api.v1.endpoints.research import router as research_router
api_router = APIRouter()
api_router.include_router(core_router)
api_router.include_router(monitoring_router)
api_router.include_router(research_router)
