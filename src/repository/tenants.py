from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.database import Tenant


async def get_by_id_repo(tenant_id: UUID, company_id: UUID, session: AsyncSession) -> Tenant | None:
    result = await session.execute(
        select(Tenant).where((Tenant.id == tenant_id) & (Tenant.company_id == company_id))
    )
    return result.scalar_one_or_none()


async def get_all_by_company_repo(company_id: UUID, session: AsyncSession) -> list[Tenant]:
    result = await session.execute(select(Tenant).where(Tenant.company_id == company_id))
    return result.scalars().all()


async def create_tenant_repo(company_id: UUID, name: str, session: AsyncSession) -> Tenant:
    tenant = Tenant(company_id=company_id, name=name)
    session.add(tenant)

    await session.commit()
    await session.refresh(tenant)

    return tenant


async def update_tenant_repo(tenant: Tenant, name: str, session: AsyncSession) -> Tenant:
    tenant.name = name

    await session.commit()
    await session.refresh(tenant)

    return tenant


async def delete_tenant_repo(tenant: Tenant, session: AsyncSession) -> None:
    await session.delete(tenant)
    await session.commit()
