import asyncio
from typing import AsyncIterator

from anthropic import Anthropic
from core.config import settings

SYSTEM_PROMPT = """Kamu adalah asisten yang menjawab pertanyaan berdasarkan dokumen yang tersedia.

Aturan:
- Jawab hanya berdasarkan konteks yang diberikan
- Jika informasi tidak ada dalam konteks, katakan dengan jelas bahwa kamu tidak menemukan informasi tersebut
- Jangan mengarang jawaban
- Jawab dalam bahasa yang sama dengan pertanyaan pengguna"""


def get_anthropic_client():
    return Anthropic(api_key=settings.anthropic_api_key)


def build_context(chunks: list[dict]) -> str:
    """Build context string from retrieved chunks"""
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        filename = chunk.get("meta", {}).get("filename", "unknown")
        context_parts.append(f"[Sumber {i} — {filename}]\n{chunk['chunk_text']}")
    return "\n\n".join(context_parts)


def query_completion(query: str, chunks: list[dict]) -> str:
    """
    Send query + context to Claude, return answer.
    One-shot completion without conversation history.
    """
    client = get_anthropic_client()
    context = build_context(chunks)

    user_message = f"""Konteks:
{context}

Pertanyaan: {query}"""

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    return response.content[0].text


def query_chat(
    query: str,
    chunks: list[dict],
    history: list[dict] | None = None,
) -> str:
    """
    Send query + context + history to Claude for multi-turn chat.
    history format: [{"role": "user"/"assistant", "content": "..."}, ...]
    """
    client = get_anthropic_client()
    context = build_context(chunks)

    current_user_message = f"""Konteks (untuk menjawab pertanyaan terbaru):
{context}

Pertanyaan: {query}"""

    messages = (history or []) + [
        {"role": "user", "content": current_user_message}
    ]

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=messages,
    )

    return response.content[0].text


async def stream_completion(query: str, chunks: list[dict]) -> AsyncIterator[str]:
    """
    Stream Claude's answer token-by-token for one-shot completion.
    Uses a queue to bridge the sync Anthropic stream into async iteration.
    """
    client = get_anthropic_client()
    context = build_context(chunks)

    user_message = f"""Konteks:
{context}

Pertanyaan: {query}"""

    queue: asyncio.Queue[str | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def _run_stream():
        try:
            with client.messages.stream(
                model="claude-haiku-4-5",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            ) as stream:
                for text in stream.text_stream:
                    loop.call_soon_threadsafe(queue.put_nowait, text)
        except Exception as e:
            loop.call_soon_threadsafe(queue.put_nowait, e)
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    loop.run_in_executor(None, _run_stream)

    while True:
        item = await queue.get()
        if item is None:
            break
        if isinstance(item, Exception):
            raise item
        yield item


async def stream_chat(
    query: str,
    chunks: list[dict],
    history: list[dict] | None = None,
) -> AsyncIterator[str]:
    """
    Stream Claude's answer token-by-token for multi-turn chat.
    history format: [{"role": "user"/"assistant", "content": "..."}, ...]
    """
    client = get_anthropic_client()
    context = build_context(chunks)

    current_user_message = f"""Konteks (untuk menjawab pertanyaan terbaru):
{context}

Pertanyaan: {query}"""

    messages = (history or []) + [
        {"role": "user", "content": current_user_message}
    ]

    queue: asyncio.Queue[str | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def _run_stream():
        try:
            with client.messages.stream(
                model="claude-haiku-4-5",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    loop.call_soon_threadsafe(queue.put_nowait, text)
        except Exception as e:
            loop.call_soon_threadsafe(queue.put_nowait, e)
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    loop.run_in_executor(None, _run_stream)

    while True:
        item = await queue.get()
        if item is None:
            break
        if isinstance(item, Exception):
            raise item
        yield item
