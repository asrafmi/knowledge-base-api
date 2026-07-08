from fastapi import APIRouter

from src.controller.v1.companies import router as companies_router
from src.controller.v1.tenants import router as tenants_router
from src.controller.v1.knowledge import router as knowledge_router
from src.controller.v1.completion import router as completion_router
from src.controller.v1.chat import router as chat_router
from src.controller.v1.conversation import router as conversation_router

router = APIRouter(prefix="/v1")

router.include_router(companies_router)
router.include_router(tenants_router)
router.include_router(knowledge_router)
router.include_router(completion_router)
router.include_router(chat_router)
router.include_router(conversation_router)

