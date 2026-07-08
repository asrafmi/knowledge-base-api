from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_session
from src.repository.tenants import get_by_id_repo


async def get_company_id(x_company_id: UUID = Header(...)) -> UUID:
    return x_company_id


async def get_tenant_id(x_tenant_id: UUID = Header(...)) -> UUID:
    return x_tenant_id


async def validate_tenant(
    company_id: UUID = Depends(get_company_id),
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> UUID:
    """Validate that tenant_id belongs to company_id"""
    tenant = await get_by_id_repo(tenant_id, company_id, session)
    if not tenant:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "tenant_not_found",
                "message": "Tenant ID tidak ditemukan atau tidak milik company ini",
            },
        )
    return tenant_id
