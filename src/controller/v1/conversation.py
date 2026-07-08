from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_company_id, validate_tenant
from src.db.session import get_session
from src.models.schemas import ConversationListResponse
from src.services.chat import get_conversations_service

router = APIRouter(prefix="/conversation", tags=["conversation"])


@router.get("", response_model=ConversationListResponse)
async def get_conversations(
    company_id: UUID = Depends(get_company_id),
    tenant_id: UUID = Depends(validate_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Get conversation history"""
    return await get_conversations_service(company_id, tenant_id, session)
