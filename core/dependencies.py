from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from models.database import Tenant


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
    result = await session.execute(
        select(Tenant).where(
            (Tenant.id == tenant_id) & (Tenant.company_id == company_id)
        )
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "tenant_not_found",
                "message": "Tenant ID tidak ditemukan atau tidak milik company ini",
            },
        )
    return tenant_id
