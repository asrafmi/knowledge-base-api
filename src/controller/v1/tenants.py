from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_company_id
from src.db.session import get_session
from src.models.schemas import TenantCreate, TenantResponse, TenantUpdate
from src.services.tenants import (
    create_tenant_service,
    delete_tenant_service,
    get_all_tenants_service,
    get_tenant_service,
    update_tenant_service,
)

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post("", response_model=TenantResponse)
async def create_tenant(
    tenant: TenantCreate,
    company_id: UUID = Depends(get_company_id),
    session: AsyncSession = Depends(get_session),
):
    db_tenant = await create_tenant_service(company_id, tenant.name, session)

    return db_tenant


@router.get("", response_model=list[TenantResponse])
async def list_tenants(
    company_id: UUID = Depends(get_company_id),
    session: AsyncSession = Depends(get_session),
):
    tenants = await get_all_tenants_service(company_id, session)

    return tenants


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID,
    company_id: UUID = Depends(get_company_id),
    session: AsyncSession = Depends(get_session),
):
    tenant = await get_tenant_service(tenant_id, company_id, session)

    return tenant


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: UUID,
    tenant: TenantUpdate,
    company_id: UUID = Depends(get_company_id),
    session: AsyncSession = Depends(get_session),
):
    db_tenant = await update_tenant_service(tenant_id, company_id, tenant.name, session)

    return db_tenant


@router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: UUID,
    company_id: UUID = Depends(get_company_id),
    session: AsyncSession = Depends(get_session),
):
    await delete_tenant_service(tenant_id, company_id, session)

    return {"status": "success"}
