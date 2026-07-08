import asyncio
from typing import AsyncIterator

from anthropic import Anthropic

from src.infrastructure.llm.base import LLMProvider


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str):
        self._client = Anthropic(api_key=api_key)

    def query(self, system_prompt: str, messages: list[dict], model: str) -> str:
        response = self._client.messages.create(
            model=model,
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
        )
        return response.content[0].text

    async def stream(self, system_prompt: str, messages: list[dict], model: str) -> AsyncIterator[str]:
        """
        Stream Claude's answer token-by-token.
        Uses a queue to bridge the sync Anthropic stream into async iteration.
        """
        queue: asyncio.Queue[str | None] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def _run_stream():
            try:
                with self._client.messages.stream(
                    model=model,
                    max_tokens=1024,
                    system=system_prompt,
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
