import voyageai
import core.config as settings

async def embed_chunks(chunks: list[str], input_type: str = "document") -> list[list[float]]:
    """
    Embed chunks using Voyage AI
    Returns list of embeddings (each is list of 1024 floats)
    """
    client = voyageai.Client(api_key=settings.voyage_api_key)

    result = await client.embed(
        texts=chunks,
        input_type=input_type,
        model="voyage-3"
    )

    return result.embeddings

async def embed_query(query: str) -> list[float]:
    """
    Embed query using Voyage AI
    Returns embedding (list of 1024 floats)
    """
    client = voyageai.Client(api_key=settings.voyage_api_key)

    result = await client.embed(
        texts=[query],
        input_type="query",
        model="voyage-3"
    )

    return result.embeddings[0]