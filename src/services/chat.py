from typing import AsyncIterator
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.schemas import (
    ChatCreateResponse,
    ChatHistoryResponse,
    ChatMessageResponse,
    ConversationListItemResponse,
    ConversationListResponse,
    MessageResponse,
    SourceChunk,
)
from src.repository.conversations import (
    create_conversation_repo,
    get_all_by_tenant_repo,
    get_by_id_repo,
)
from src.repository.messages import create_messages_repo, get_all_by_conversation_repo
from src.services.llm import query_chat, stream_chat
from src.services.retrieval import retrieve_chunks


async def create_conversation_service(
    company_id: UUID, tenant_id: UUID, user_id: str | None, session: AsyncSession
) -> ChatCreateResponse:
    conversation = await create_conversation_repo(company_id, tenant_id, user_id, session)

    return ChatCreateResponse(
        conversation_id=conversation.id,
        created_at=conversation.created_at,
    )


async def _get_conversation_or_404(
    conversation_id: UUID, company_id: UUID, tenant_id: UUID, session: AsyncSession
):
    conversation = await get_by_id_repo(conversation_id, company_id, tenant_id, session)
    if not conversation:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "conversation_not_found",
                "message": "Conversation not found or does not belong to this tenant",
            },
        )
    return conversation


async def _retrieve_context_or_404(
    message: str, company_id: UUID, tenant_id: UUID, session: AsyncSession
) -> list[dict]:
    try:
        chunks = await retrieve_chunks(
            query=message,
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

    return chunks


async def send_message_service(
    conversation_id: UUID,
    message: str,
    company_id: UUID,
    tenant_id: UUID,
    session: AsyncSession,
) -> ChatMessageResponse:
    if not message.strip():
        raise HTTPException(
            status_code=400,
            detail={"error": "empty_message", "message": "Message cannot be empty"},
        )

    await _get_conversation_or_404(conversation_id, company_id, tenant_id, session)

    chunks = await _retrieve_context_or_404(message, company_id, tenant_id, session)

    history_messages = await get_all_by_conversation_repo(conversation_id, session)
    history = [{"role": msg.role, "content": msg.content} for msg in history_messages]

    try:
        answer = query_chat(message, chunks, history=history)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "completion_error",
                "message": f"Failed to generate answer: {str(e)}",
            },
        )

    await create_messages_repo(conversation_id, message, answer, session)

    sources = [
        SourceChunk(document_id=chunk["document_id"], chunk_index=chunk["chunk_index"])
        for chunk in chunks
    ]

    return ChatMessageResponse(
        conversation_id=conversation_id,
        answer=answer,
        sources=sources,
    )


async def get_history_service(
    conversation_id: UUID, company_id: UUID, tenant_id: UUID, session: AsyncSession
) -> ChatHistoryResponse:
    await _get_conversation_or_404(conversation_id, company_id, tenant_id, session)

    messages = await get_all_by_conversation_repo(conversation_id, session)

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


async def prepare_message_stream_service(
    conversation_id: UUID,
    message: str,
    company_id: UUID,
    tenant_id: UUID,
    session: AsyncSession,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Validate + retrieve everything needed before streaming starts. Returns (chunks, sources, history)."""
    if not message.strip():
        raise HTTPException(
            status_code=400,
            detail={"error": "empty_message", "message": "Message cannot be empty"},
        )

    await _get_conversation_or_404(conversation_id, company_id, tenant_id, session)

    chunks = await _retrieve_context_or_404(message, company_id, tenant_id, session)

    history_messages = await get_all_by_conversation_repo(conversation_id, session)
    history = [{"role": msg.role, "content": msg.content} for msg in history_messages]

    sources = [
        {"document_id": str(chunk["document_id"]), "chunk_index": chunk["chunk_index"]}
        for chunk in chunks
    ]

    return chunks, sources, history


async def stream_message_service(
    message: str, chunks: list[dict], history: list[dict]
) -> AsyncIterator[str]:
    async for text in stream_chat(message, chunks, history=history):
        yield text


async def save_stream_result_service(
    conversation_id: UUID, message: str, full_text: str, session: AsyncSession
) -> None:
    await create_messages_repo(conversation_id, message, full_text, session)


async def get_conversations_service(
    company_id: UUID, tenant_id: UUID, session: AsyncSession
) -> ConversationListResponse:
    conversations = await get_all_by_tenant_repo(company_id, tenant_id, session)

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
