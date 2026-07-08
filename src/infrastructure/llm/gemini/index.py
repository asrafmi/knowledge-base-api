from typing import AsyncIterator

from google import genai
from google.genai import types

from src.infrastructure.llm.base import LLMProvider


def _to_gemini_contents(messages: list[dict]) -> list[types.Content]:
    return [
        types.Content(
            role="model" if msg["role"] == "assistant" else "user",
            parts=[types.Part.from_text(text=msg["content"])],
        )
        for msg in messages
    ]


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str):
        self._client = genai.Client(api_key=api_key)

    def query(self, system_prompt: str, messages: list[dict], model: str) -> str:
        response = self._client.models.generate_content(
            model=model,
            contents=_to_gemini_contents(messages),
            config=types.GenerateContentConfig(system_instruction=system_prompt),
        )
        return response.text

    async def stream(self, system_prompt: str, messages: list[dict], model: str) -> AsyncIterator[str]:
        stream = await self._client.aio.models.generate_content_stream(
            model=model,
            contents=_to_gemini_contents(messages),
            config=types.GenerateContentConfig(system_instruction=system_prompt),
        )
        async for chunk in stream:
            if chunk.text:
                yield chunk.text
