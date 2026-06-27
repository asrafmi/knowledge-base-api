from fastapi import APIRouter

from api.v1.companies import router as companies_router
from api.v1.tenants import router as tenants_router
from api.v1.knowledge import router as knowledge_router

router = APIRouter(prefix="/v1")

router.include_router(companies_router)
router.include_router(tenants_router)
router.include_router(knowledge_router)
