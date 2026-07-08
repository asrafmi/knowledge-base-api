from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_company_id, validate_tenant
from src.core.sse import sse_event
from src.db.session import get_session
from src.infrastructure.llm.base import build_context
from src.models.schemas import CompletionRequest, CompletionResponse, SourceChunk
from src.services.retrieval import retrieve_chunks
from src.services.tenant_llm_settings import resolve_llm_config_service


def _build_completion_message(query: str, chunks: list[dict]) -> list[dict]:
    context = build_context(chunks)
    user_message = f"""Konteks:
{context}

Pertanyaan: {query}"""
    return [{"role": "user", "content": user_message}]

router = APIRouter(prefix="/completion", tags=["completion"])


@router.post("", response_model=CompletionResponse)
async def completion(
    request: CompletionRequest,
    company_id: UUID = Depends(get_company_id),
    tenant_id: UUID = Depends(validate_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Query knowledge base and get answer (one-shot, no history)"""

    if not request.query.strip():
        raise HTTPException(
            status_code=400,
            detail={
                "error": "empty_query",
                "message": "Query cannot be empty",
            },
        )

    try:
        chunks = await retrieve_chunks(
            query=request.query,
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

    try:
        provider, model, system_prompt = await resolve_llm_config_service(tenant_id, session)
        messages = _build_completion_message(request.query, chunks)
        answer = provider.query(system_prompt, messages, model)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "completion_error",
                "message": f"Failed to generate answer: {str(e)}",
            },
        )

    sources = [
        SourceChunk(document_id=chunk["document_id"], chunk_index=chunk["chunk_index"])
        for chunk in chunks
    ]

    return CompletionResponse(answer=answer, sources=sources)


@router.post("/stream")
async def completion_stream(
    request: CompletionRequest,
    company_id: UUID = Depends(get_company_id),
    tenant_id: UUID = Depends(validate_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Query knowledge base and stream answer token-by-token (SSE)"""

    if not request.query.strip():
        raise HTTPException(
            status_code=400,
            detail={
                "error": "empty_query",
                "message": "Query cannot be empty",
            },
        )

    try:
        chunks = await retrieve_chunks(
            query=request.query,
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

    sources = [
        {"document_id": str(chunk["document_id"]), "chunk_index": chunk["chunk_index"]}
        for chunk in chunks
    ]

    provider, model, system_prompt = await resolve_llm_config_service(tenant_id, session)
    messages = _build_completion_message(request.query, chunks)

    async def event_generator():
        try:
            async for text in provider.stream(system_prompt, messages, model):
                yield sse_event({"text": text})
            yield sse_event({"sources": sources}, event="done")
        except Exception as e:
            yield sse_event(
                {"error": "completion_error", "message": str(e)}, event="error"
            )

    return StreamingResponse(event_generator(), media_type="text/event-stream")
