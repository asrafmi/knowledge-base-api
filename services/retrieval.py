import asyncio
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pgvector.sqlalchemy import Vector

from models.database import DocumentChunks
from infrastructure.voyage.index import embed_query


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

    result = await session.execute(
        select(DocumentChunks)
        .where(
            (DocumentChunks.company_id == company_id)
            & (DocumentChunks.tenant_id == tenant_id)
            & (DocumentChunks.embedding.is_not(None))
        )
        .order_by(DocumentChunks.embedding.cosine_distance(query_embedding))
        .limit(top_k)
    )

    chunks = result.scalars().all()

    return [
        {
            "document_id": chunk.document_id,
            "chunk_index": chunk.chunk_index,
            "chunk_text": chunk.chunk_text,
            "meta": chunk.meta or {},
        }
        for chunk in chunks
    ]
