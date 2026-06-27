import voyageai
from core.config import settings
from functools import lru_cache


@lru_cache(maxsize=1)
def get_voyage_client():
    return voyageai.Client(api_key=settings.voyage_api_key)


def embed_chunks(chunks: list[str], input_type: str = "document") -> list[list[float]]:
    """
    Embed chunks using Voyage AI
    Returns list of embeddings (each is list of 1024 floats)
    """
    client = get_voyage_client()
    result = client.embed(
        texts=chunks,
        input_type=input_type,
        model="voyage-4"
    )
    return result.embeddings


def embed_query(query: str) -> list[float]:
    """
    Embed query using Voyage AI
    Returns embedding (list of 1024 floats)
    """
    client = get_voyage_client()
    result = client.embed(
        texts=[query],
        input_type="query",
        model="voyage-4"
    )
    return result.embeddings[0]

