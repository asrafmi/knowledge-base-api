from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_company_id, validate_tenant
from src.db.session import get_session
from src.models.schemas import LLMSettingsResponse, LLMSettingsUpdate
from src.services.tenant_llm_settings import get_settings_service, update_settings_service

router = APIRouter(prefix="/llm-settings", tags=["llm-settings"])


@router.get("", response_model=LLMSettingsResponse)
async def get_llm_settings(
    company_id: UUID = Depends(get_company_id),
    tenant_id: UUID = Depends(validate_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Get tenant's LLM provider settings (never exposes the API key itself)"""
    return await get_settings_service(tenant_id, session)


@router.put("", response_model=LLMSettingsResponse)
async def update_llm_settings(
    settings_update: LLMSettingsUpdate,
    company_id: UUID = Depends(get_company_id),
    tenant_id: UUID = Depends(validate_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Create or update tenant's LLM provider settings"""
    return await update_settings_service(
        tenant_id,
        company_id,
        settings_update.provider,
        settings_update.model,
        settings_update.api_key,
        settings_update.system_prompt,
        session,
    )
