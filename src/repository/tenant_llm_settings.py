from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.database import TenantLLMSettings


async def get_by_tenant_repo(tenant_id: UUID, session: AsyncSession) -> TenantLLMSettings | None:
    result = await session.execute(
        select(TenantLLMSettings).where(TenantLLMSettings.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def upsert_repo(
    tenant_id: UUID,
    company_id: UUID,
    provider: str,
    model: str,
    api_key_encrypted: str | None,
    system_prompt: str | None,
    session: AsyncSession,
) -> TenantLLMSettings:
    settings_row = await get_by_tenant_repo(tenant_id, session)

    if settings_row is None:
        settings_row = TenantLLMSettings(tenant_id=tenant_id, company_id=company_id)
        session.add(settings_row)

    settings_row.provider = provider
    settings_row.model = model
    settings_row.api_key_encrypted = api_key_encrypted
    settings_row.system_prompt = system_prompt

    await session.commit()
    await session.refresh(settings_row)

    return settings_row
