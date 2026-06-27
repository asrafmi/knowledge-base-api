from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_company_id, validate_tenant
from db.session import get_session
from models.schemas import CompletionRequest, CompletionResponse, SourceChunk
from services.retrieval import retrieve_chunks
from services.llm import query_completion

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
        answer = query_completion(request.query, chunks)
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
