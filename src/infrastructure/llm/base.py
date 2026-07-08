from abc import ABC, abstractmethod
from typing import AsyncIterator

DEFAULT_SYSTEM_PROMPT = """Kamu adalah asisten yang menjawab pertanyaan berdasarkan dokumen yang tersedia.

Jawab dalam bahasa yang sama dengan pertanyaan pengguna, jika bahasa inggris, jawab dalam bahasa inggris, jika bahasa indonesia, jawab dalam bahasa indonesia."""

RAG_GUARDRAIL_PROMPT = """Aturan wajib (tidak bisa diubah):
- Jawab hanya berdasarkan konteks yang diberikan
- Jika informasi tidak ada dalam konteks, katakan dengan jelas bahwa kamu tidak menemukan informasi tersebut
- Jangan mengarang jawaban"""

PROVIDER_MODELS: dict[str, list[str]] = {
    "anthropic": ["claude-sonnet-4-5-20250929", "claude-haiku-4-5"],
    "openai": ["gpt-5.4", "gpt-5.4-mini"],
    "gemini": ["gemini-2.5-flash", "gemini-3-flash"],
}


def build_context(chunks: list[dict]) -> str:
    """Build context string from retrieved chunks. Provider-agnostic."""
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        filename = chunk.get("meta", {}).get("filename", "unknown")
        context_parts.append(f"[Sumber {i} — {filename}]\n{chunk['chunk_text']}")
    return "\n\n".join(context_parts)


class LLMProvider(ABC):
    """Common interface every LLM provider integration must implement."""

    @abstractmethod
    def query(self, system_prompt: str, messages: list[dict], model: str) -> str:
        """Send messages to the LLM, return the full answer text (no history mutation)."""
        ...

    @abstractmethod
    def stream(self, system_prompt: str, messages: list[dict], model: str) -> AsyncIterator[str]:
        """Stream the LLM's answer token-by-token."""
        ...
