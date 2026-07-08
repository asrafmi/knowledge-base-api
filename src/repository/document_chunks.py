from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.database import DocumentChunks


async def count_by_document_repo(document_id: UUID, session: AsyncSession) -> int:
    result = await session.execute(
        select(DocumentChunks).where(DocumentChunks.document_id == document_id)
    )
    return len(result.scalars().all())


async def create_chunks_repo(
    document_id: UUID,
    company_id: UUID,
    tenant_id: UUID,
    chunks: list[str],
    embeddings: list[list[float]] | None,
    session: AsyncSession,
) -> list[DocumentChunks]:
    chunk_records = [
        DocumentChunks(
            document_id=document_id,
            company_id=company_id,
            tenant_id=tenant_id,
            chunk_text=chunk,
            chunk_index=i,
            embedding=embeddings[i] if embeddings else None,
            meta={"chunk_size_tokens": len(chunk.split())},
        )
        for i, chunk in enumerate(chunks)
    ]
    session.add_all(chunk_records)

    return chunk_records


async def search_by_similarity_repo(
    query_embedding: list[float],
    company_id: UUID,
    tenant_id: UUID,
    top_k: int,
    session: AsyncSession,
) -> list[DocumentChunks]:
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
    return result.scalars().all()
