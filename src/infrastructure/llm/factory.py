from src.core.config import settings
from src.infrastructure.llm.anthropic.index import AnthropicProvider
from src.infrastructure.llm.base import LLMProvider
from src.infrastructure.llm.gemini.index import GeminiProvider
from src.infrastructure.llm.openai.index import OpenAIProvider

_DEFAULT_API_KEYS = {
    "anthropic": lambda: settings.anthropic_api_key,
    "openai": lambda: settings.openai_api_key,
    "gemini": lambda: settings.gemini_api_key,
}

_PROVIDER_CLASSES: dict[str, type[LLMProvider]] = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
}


def get_llm_provider(provider: str, api_key: str | None) -> LLMProvider:
    """Resolve a provider instance. api_key=None falls back to our own default key for that provider."""
    resolved_key = api_key or _DEFAULT_API_KEYS[provider]()
    return _PROVIDER_CLASSES[provider](api_key=resolved_key)
