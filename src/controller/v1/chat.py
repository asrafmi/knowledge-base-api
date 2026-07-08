from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi.responses import StreamingResponse

from src.core.dependencies import get_company_id, validate_tenant
from src.core.sse import sse_event
from src.db.session import get_session
from src.models.schemas import (
    ChatCreateRequest,
    ChatCreateResponse,
    MessageRequest,
    ChatMessageResponse,
    ChatHistoryResponse,
)
from src.services.chat import (
    create_conversation_service,
    get_history_service,
    prepare_message_stream_service,
    save_stream_result_service,
    send_message_service,
    stream_message_service,
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatCreateResponse)
async def create_conversation(
    request: ChatCreateRequest,
    company_id: UUID = Depends(get_company_id),
    tenant_id: UUID = Depends(validate_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Create new conversation"""
    return await create_conversation_service(company_id, tenant_id, request.user_id, session)


@router.post("/{conversation_id}/message", response_model=ChatMessageResponse)
async def send_message(
    conversation_id: UUID,
    request: MessageRequest,
    company_id: UUID = Depends(get_company_id),
    tenant_id: UUID = Depends(validate_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Send message to conversation and get response"""
    return await send_message_service(
        conversation_id, request.message, company_id, tenant_id, session
    )


@router.get("/{conversation_id}/history", response_model=ChatHistoryResponse)
async def get_history(
    conversation_id: UUID,
    company_id: UUID = Depends(get_company_id),
    tenant_id: UUID = Depends(validate_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Get conversation history"""
    return await get_history_service(conversation_id, company_id, tenant_id, session)


@router.post("/{conversation_id}/message/stream")
async def send_message_stream(
    conversation_id: UUID,
    request: MessageRequest,
    company_id: UUID = Depends(get_company_id),
    tenant_id: UUID = Depends(validate_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Send message to conversation and stream response token-by-token (SSE)"""
    chunks, sources, history = await prepare_message_stream_service(
        conversation_id, request.message, company_id, tenant_id, session
    )

    user_message_text = request.message

    async def event_generator():
        full_text = ""
        try:
            async for text in stream_message_service(user_message_text, chunks, history):
                full_text += text
                yield sse_event({"text": text})

            # Save both messages only after successful stream completion
            await save_stream_result_service(conversation_id, user_message_text, full_text, session)

            yield sse_event(
                {"sources": sources, "conversation_id": str(conversation_id)},
                event="done",
            )
        except Exception as e:
            yield sse_event(
                {"error": "completion_error", "message": str(e)}, event="error"
            )

    return StreamingResponse(event_generator(), media_type="text/event-stream")
