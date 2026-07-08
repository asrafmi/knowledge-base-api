from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.database import Documents


async def get_all_by_tenant_repo(company_id: UUID, tenant_id: UUID, session: AsyncSession) -> list[Documents]:
    result = await session.execute(
        select(Documents).where(
            (Documents.company_id == company_id) & (Documents.tenant_id == tenant_id)
        )
    )
    return result.scalars().all()


async def get_by_id_repo(
    document_id: UUID, company_id: UUID, tenant_id: UUID, session: AsyncSession
) -> Documents | None:
    result = await session.execute(
        select(Documents).where(
            (Documents.id == document_id)
            & (Documents.company_id == company_id)
            & (Documents.tenant_id == tenant_id)
        )
    )
    return result.scalar_one_or_none()


async def create_document_repo(
    company_id: UUID,
    tenant_id: UUID,
    filename: str,
    content_type: str | None,
    meta: dict,
    session: AsyncSession,
) -> Documents:
    document = Documents(
        company_id=company_id,
        tenant_id=tenant_id,
        filename=filename,
        content_type=content_type,
        meta=meta,
    )
    session.add(document)
    await session.flush()  # populate document.id before chunks reference it

    return document


async def delete_document_repo(document: Documents, session: AsyncSession) -> None:
    await session.delete(document)
    await session.commit()
