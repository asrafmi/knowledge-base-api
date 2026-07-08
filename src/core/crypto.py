from functools import lru_cache

from cryptography.fernet import Fernet

from src.core.config import settings


@lru_cache
def _get_fernet() -> Fernet:
    return Fernet(settings.llm_settings_encryption_key.encode())


def encrypt_api_key(raw: str) -> str:
    return _get_fernet().encrypt(raw.encode()).decode()


def decrypt_api_key(token: str) -> str:
    return _get_fernet().decrypt(token.encode()).decode()
