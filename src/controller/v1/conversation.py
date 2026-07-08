from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_company_id, validate_tenant
from src.db.session import get_session
from src.models.database import Conversations, Messages
from src.models.schemas import (
    ConversationListItemResponse,
    ConversationListResponse,
)

router = APIRouter(prefix="/conversation", tags=["conversation"])

@router.get("", response_model=ConversationListResponse)
async def get_conversations(
    company_id: UUID = Depends(get_company_id),
    tenant_id: UUID = Depends(validate_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Get conversation history"""

    result = await session.execute(
        select(Conversations).where(
            (Conversations.company_id == company_id)
            & (Conversations.tenant_id == tenant_id)
        )
    )
    conversations = result.scalars().all()

    if not conversations:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "conversation_not_found",
                "message": "Conversation not found or does not belong to this tenant",
            },
        )

    return ConversationListResponse(
        conversations=[
            ConversationListItemResponse(
                conversation_id=conv.id,
                created_at=conv.created_at,
            )
            for conv in conversations
        ]
    )
