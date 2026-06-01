from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_company_id
from db.session import get_session
from models.database import Company, Tenant
from models.schemas import TenantCreate, TenantResponse, TenantUpdate

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post("", response_model=TenantResponse)
async def create_tenant(
    tenant: TenantCreate,
    company_id: UUID = Depends(get_company_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(
            status_code=404,
            detail={"error": "company_not_found", "message": "Company tidak ditemukan"},
        )

    db_tenant = Tenant(company_id=company_id, name=tenant.name)
    session.add(db_tenant)
    await session.commit()
    await session.refresh(db_tenant)
    return db_tenant


@router.get("", response_model=list[TenantResponse])
async def list_tenants(
    company_id: UUID = Depends(get_company_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Tenant).where(Tenant.company_id == company_id)
    )
    tenants = result.scalars().all()
    return tenants


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID,
    company_id: UUID = Depends(get_company_id),
    session: AsyncSession = Depends(get_session),
):
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
    return tenant


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: UUID,
    tenant: TenantUpdate,
    company_id: UUID = Depends(get_company_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Tenant).where(
            (Tenant.id == tenant_id) & (Tenant.company_id == company_id)
        )
    )
    db_tenant = result.scalar_one_or_none()
    if not db_tenant:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "tenant_not_found",
                "message": "Tenant ID tidak ditemukan atau tidak milik company ini",
            },
        )
    db_tenant.name = tenant.name
    await session.commit()
    await session.refresh(db_tenant)
    return db_tenant


@router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: UUID,
    company_id: UUID = Depends(get_company_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Tenant).where(
            (Tenant.id == tenant_id) & (Tenant.company_id == company_id)
        )
    )
    db_tenant = result.scalar_one_or_none()
    if not db_tenant:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "tenant_not_found",
                "message": "Tenant ID tidak ditemukan atau tidak milik company ini",
            },
        )
    await session.delete(db_tenant)
    await session.commit()
    return {"status": "success"}
