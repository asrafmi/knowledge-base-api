from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.database import Tenant
from src.repository.companies import get_by_id_repo as get_company_by_id_repo
from src.repository.tenants import (
    create_tenant_repo,
    delete_tenant_repo,
    get_all_by_company_repo,
    get_by_id_repo,
    update_tenant_repo,
)


async def get_tenant_service(tenant_id: UUID, company_id: UUID, session: AsyncSession) -> Tenant:
    tenant = await get_by_id_repo(tenant_id, company_id, session)
    if not tenant:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "tenant_not_found",
                "message": "Tenant ID tidak ditemukan atau tidak milik company ini",
            },
        )

    return tenant


async def get_all_tenants_service(company_id: UUID, session: AsyncSession) -> list[Tenant]:
    tenants = await get_all_by_company_repo(company_id, session)

    return tenants


async def create_tenant_service(company_id: UUID, name: str, session: AsyncSession) -> Tenant:
    company = await get_company_by_id_repo(company_id, session)
    if not company:
        raise HTTPException(
            status_code=404,
            detail={"error": "company_not_found", "message": "Company tidak ditemukan"},
        )

    tenant = await create_tenant_repo(company_id, name, session)

    return tenant


async def update_tenant_service(
    tenant_id: UUID, company_id: UUID, name: str, session: AsyncSession
) -> Tenant:
    tenant = await get_tenant_service(tenant_id, company_id, session)
    tenant = await update_tenant_repo(tenant, name, session)

    return tenant


async def delete_tenant_service(tenant_id: UUID, company_id: UUID, session: AsyncSession) -> None:
    tenant = await get_tenant_service(tenant_id, company_id, session)
    await delete_tenant_repo(tenant, session)
