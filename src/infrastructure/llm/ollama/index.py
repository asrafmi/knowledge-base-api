import json
from typing import AsyncIterator

import httpx

from src.infrastructure.llm.base import LLMProvider


class OllamaProvider(LLMProvider):
    """Self-hosted provider — talks to a plain Ollama server, no API key required."""

    def __init__(self, base_url: str):
        self._base_url = base_url.rstrip("/")

    def query(self, system_prompt: str, messages: list[dict], model: str) -> str:
        response = httpx.post(
            f"{self._base_url}/api/chat",
            json={
                "model": model,
                "messages": [{"role": "system", "content": system_prompt}, *messages],
                "stream": False,
            },
            timeout=120.0,
        )
        response.raise_for_status()
        return response.json()["message"]["content"]

    async def stream(self, system_prompt: str, messages: list[dict], model: str) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/api/chat",
                json={
                    "model": model,
                    "messages": [{"role": "system", "content": system_prompt}, *messages],
                    "stream": True,
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    delta = chunk.get("message", {}).get("content")
                    if delta:
                        yield delta
