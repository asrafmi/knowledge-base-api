from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.crypto import decrypt_api_key, encrypt_api_key
from src.infrastructure.llm.base import DEFAULT_SYSTEM_PROMPT, PROVIDER_MODELS, RAG_GUARDRAIL_PROMPT
from src.infrastructure.llm.factory import get_llm_provider, LLMProvider
from src.models.schemas import LLMSettingsResponse
from src.repository.tenant_llm_settings import get_by_tenant_repo, upsert_repo

DEFAULT_PROVIDER = "anthropic"
DEFAULT_MODEL = "claude-haiku-4-5"


def _validate_provider_and_model(provider: str, model: str) -> None:
    if provider not in PROVIDER_MODELS:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_provider",
                "message": f"Provider must be one of: {', '.join(PROVIDER_MODELS.keys())}",
            },
        )

    # ollama is self-hosted — model names depend on what the tenant pulled on their own
    # server, so there's no fixed whitelist to validate against.
    if provider == "ollama":
        return

    if model not in PROVIDER_MODELS[provider]:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_model",
                "message": f"Model for provider '{provider}' must be one of: {', '.join(PROVIDER_MODELS[provider])}",
            },
        )


async def get_settings_service(tenant_id: UUID, session: AsyncSession) -> LLMSettingsResponse:
    settings_row = await get_by_tenant_repo(tenant_id, session)

    if settings_row is None:
        return LLMSettingsResponse(
            provider=DEFAULT_PROVIDER,
            model=DEFAULT_MODEL,
            has_custom_api_key=False,
            base_url=None,
            system_prompt=None,
            updated_at=None,
        )

    return LLMSettingsResponse(
        provider=settings_row.provider,
        model=settings_row.model,
        has_custom_api_key=settings_row.api_key_encrypted is not None,
        base_url=settings_row.base_url,
        system_prompt=settings_row.system_prompt,
        updated_at=settings_row.updated_at,
    )


async def update_settings_service(
    tenant_id: UUID,
    company_id: UUID,
    provider: str,
    model: str,
    api_key: str | None,
    base_url: str | None,
    system_prompt: str | None,
    session: AsyncSession,
) -> LLMSettingsResponse:
    _validate_provider_and_model(provider, model)

    api_key_encrypted = encrypt_api_key(api_key) if api_key else None

    settings_row = await upsert_repo(
        tenant_id, company_id, provider, model, api_key_encrypted, base_url, system_prompt, session
    )

    return LLMSettingsResponse(
        provider=settings_row.provider,
        model=settings_row.model,
        has_custom_api_key=settings_row.api_key_encrypted is not None,
        base_url=settings_row.base_url,
        system_prompt=settings_row.system_prompt,
        updated_at=settings_row.updated_at,
    )


async def resolve_llm_config_service(
    tenant_id: UUID, session: AsyncSession
) -> tuple[LLMProvider, str, str]:
    """Resolve (provider_instance, model, final_system_prompt) for a tenant's RAG calls."""
    settings_row = await get_by_tenant_repo(tenant_id, session)

    if settings_row is None:
        provider_name = DEFAULT_PROVIDER
        model = DEFAULT_MODEL
        api_key = None
        base_url = None
        custom_prompt = None
    else:
        provider_name = settings_row.provider
        model = settings_row.model
        api_key = (
            decrypt_api_key(settings_row.api_key_encrypted)
            if settings_row.api_key_encrypted
            else None
        )
        base_url = settings_row.base_url
        custom_prompt = settings_row.system_prompt

    provider = get_llm_provider(provider_name, api_key, base_url)
    final_system_prompt = f"{custom_prompt or DEFAULT_SYSTEM_PROMPT}\n\n{RAG_GUARDRAIL_PROMPT}"

    return provider, model, final_system_prompt
