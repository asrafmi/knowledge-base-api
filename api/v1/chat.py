from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_company_id, validate_tenant
from db.session import get_session
from models.database import Conversations, Messages
from models.schemas import (
    ChatCreateRequest,
    ChatCreateResponse,
    MessageRequest,
    ChatMessageResponse,
    ChatHistoryResponse,
    MessageResponse,
    SourceChunk,
)
from services.retrieval import retrieve_chunks
from services.llm import query_chat

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatCreateResponse)
async def create_conversation(
    request: ChatCreateRequest,
    company_id: UUID = Depends(get_company_id),
    tenant_id: UUID = Depends(validate_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Create new conversation"""

    conversation = Conversations(
        company_id=company_id,
        tenant_id=tenant_id,
        user_id=request.user_id,
    )
    session.add(conversation)
    await session.commit()

    return ChatCreateResponse(
        conversation_id=conversation.id,
        created_at=conversation.created_at,
    )


@router.post("/{conversation_id}/message", response_model=ChatMessageResponse)
async def send_message(
    conversation_id: UUID,
    request: MessageRequest,
    company_id: UUID = Depends(get_company_id),
    tenant_id: UUID = Depends(validate_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Send message to conversation and get response"""

    if not request.message.strip():
        raise HTTPException(
            status_code=400,
            detail={
                "error": "empty_message",
                "message": "Message cannot be empty",
            },
        )

    result = await session.execute(
        select(Conversations).where(
            (Conversations.id == conversation_id)
            & (Conversations.company_id == company_id)
            & (Conversations.tenant_id == tenant_id)
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "conversation_not_found",
                "message": "Conversation not found or does not belong to this tenant",
            },
        )

    # Retrieve context
    try:
        chunks = await retrieve_chunks(
            query=request.message,
            company_id=company_id,
            tenant_id=tenant_id,
            session=session,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "retrieval_error",
                "message": f"Failed to retrieve context: {str(e)}",
            },
        )

    if not chunks:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "no_context",
                "message": "No relevant documents found in knowledge base",
            },
        )

    # Fetch conversation history
    history_result = await session.execute(
        select(Messages)
        .where(Messages.conversation_id == conversation_id)
        .order_by(Messages.created_at.asc())
    )
    history_messages = history_result.scalars().all()

    # Build history for Claude (without last message which will be the new one)
    history = [
        {"role": msg.role, "content": msg.content} for msg in history_messages
    ]

    # Generate response
    try:
        answer = query_chat(request.message, chunks, history=history)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "completion_error",
                "message": f"Failed to generate answer: {str(e)}",
            },
        )

    # Save messages to database
    user_msg = Messages(
        conversation_id=conversation_id,
        role="user",
        content=request.message,
    )
    assistant_msg = Messages(
        conversation_id=conversation_id,
        role="assistant",
        content=answer,
    )
    session.add_all([user_msg, assistant_msg])
    await session.commit()

    sources = [
        SourceChunk(document_id=chunk["document_id"], chunk_index=chunk["chunk_index"])
        for chunk in chunks
    ]

    return ChatMessageResponse(
        conversation_id=conversation_id,
        answer=answer,
        sources=sources,
    )


@router.get("/{conversation_id}/history", response_model=ChatHistoryResponse)
async def get_history(
    conversation_id: UUID,
    company_id: UUID = Depends(get_company_id),
    tenant_id: UUID = Depends(validate_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Get conversation history"""

    result = await session.execute(
        select(Conversations).where(
            (Conversations.id == conversation_id)
            & (Conversations.company_id == company_id)
            & (Conversations.tenant_id == tenant_id)
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "conversation_not_found",
                "message": "Conversation not found or does not belong to this tenant",
            },
        )

    messages_result = await session.execute(
        select(Messages)
        .where(Messages.conversation_id == conversation_id)
        .order_by(Messages.created_at.asc())
    )
    messages = messages_result.scalars().all()

    return ChatHistoryResponse(
        messages=[
            MessageResponse(
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at,
            )
            for msg in messages
        ]
    )
