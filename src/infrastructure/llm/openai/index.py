from typing import AsyncIterator

from openai import AsyncOpenAI, OpenAI

from src.infrastructure.llm.base import LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str):
        self._client = OpenAI(api_key=api_key)
        self._async_client = AsyncOpenAI(api_key=api_key)

    def query(self, system_prompt: str, messages: list[dict], model: str) -> str:
        response = self._client.chat.completions.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "system", "content": system_prompt}, *messages],
        )
        return response.choices[0].message.content

    async def stream(self, system_prompt: str, messages: list[dict], model: str) -> AsyncIterator[str]:
        stream = await self._async_client.chat.completions.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "system", "content": system_prompt}, *messages],
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
