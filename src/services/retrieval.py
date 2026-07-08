import asyncio
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.voyage.index import embed_query
from src.repository.document_chunks import search_by_similarity_repo


async def retrieve_chunks(
    query: str,
    company_id: UUID,
    tenant_id: UUID,
    session: AsyncSession,
    top_k: int = 5,
) -> list[dict]:
    """
    Retrieve top-k chunks via vector similarity search.
    Returns list of dicts with chunk info for RAG context.
    """
    query_embedding = await asyncio.to_thread(embed_query, query)

    chunks = await search_by_similarity_repo(
        query_embedding, company_id, tenant_id, top_k, session
    )

    return [
        {
            "document_id": chunk.document_id,
            "chunk_index": chunk.chunk_index,
            "chunk_text": chunk.chunk_text,
            "meta": chunk.meta or {},
        }
        for chunk in chunks
    ]
