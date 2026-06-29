# Phase 3: SSE Streaming untuk Completion & Chat

Realtime token-by-token streaming untuk jawaban Claude, tanpa WebSocket/Socket.IO.

## Overview

Tambahkan varian streaming untuk endpoint yang sudah ada:
- `POST /v1/completion/stream` — one-shot completion, stream token jawaban
- `POST /v1/chat/{conversation_id}/message/stream` — multi-turn chat, stream token jawaban

**Keputusan arsitektur**: pakai **Server-Sent Events (SSE)**, bukan Socket.IO/WebSocket.

**Kenapa bukan Socket.IO:**
- Kebutuhan cuma streaming token jawaban (request → stream response), bukan bidirectional/presence/multi-device sync
- Anthropic SDK sudah native support streaming (`client.messages.stream()`) yang langsung cocok di-pipe ke HTTP stream
- Tidak perlu infra tambahan: no connection lifecycle, no room/namespace, no dependency baru (`python-socketio`)
- Auth tetap pakai header `X-Company-ID`/`X-Tenant-ID` via `Depends` yang sudah ada — tidak perlu reimplement auth di socket handshake
- Browser native support via `EventSource`, lolos load balancer/proxy tanpa konfigurasi khusus
- Konsisten dengan pola REST yang sudah ada — endpoint baru, response-nya saja yang berubah jadi stream

**Bedanya dengan endpoint REST existing**: response dikirim sebagai `text/event-stream` chunk-by-chunk, bukan satu JSON body. Untuk endpoint chat, commit ke database baru terjadi **setelah** generator selesai (bukan sebelum response dikirim), karena kita harus accumulate full text dulu sebelum di-save sebagai `assistant` message.

**Endpoint lama (`POST /v1/completion`, `POST /v1/chat/{id}/message`) tetap ada, tidak diubah** — dipisah jadi endpoint baru, bukan overload dengan query param, supaya `response_model` REST yang lama tetap jelas dan tidak bercampur tipe response.

**Timeline**: ~40 menit (5 steps)

---

## Step 1: SSE Helper

**File**: `core/sse.py` (baru)

**Time**: 5 min

Helper kecil untuk format event sesuai spec SSE (`data: <json>\n\n`), dipakai bersama oleh completion & chat stream.

```python
import json
from typing import Any


def sse_event(data: dict[str, Any], event: str | None = None) -> str:
    """Format a single SSE event. event=None -> default 'message' event."""
    payload = f"data: {json.dumps(data)}\n\n"
    if event:
        payload = f"event: {event}\n{payload}"
    return payload
```

Event types yang dipakai di stream ini:
- default (`data:` tanpa `event:`) — text delta, payload `{"text": "..."}`
- `event: done` — stream selesai sukses, payload berisi `sources` (dan `conversation_id` untuk chat)
- `event: error` — error terjadi setelah stream mulai, payload `{"error": "...", "message": "..."}`

---

## Step 2: Streaming di LLM Service

**File**: `services/llm.py`

**Time**: 15 min

Tambah dua fungsi generator baru, **tidak mengubah** `query_completion` dan `query_chat` yang sudah ada (tetap dipakai endpoint non-stream).

```python
from typing import AsyncIterator

async def stream_completion(query: str, chunks: list[dict]) -> AsyncIterator[str]:
    """
    Stream Claude's answer token-by-token.
    Yields raw text deltas (no SSE framing — itu tugas endpoint layer).
    """
    client = get_anthropic_client()
    context = build_context(chunks)

    user_message = f"""Konteks:
{context}

Pertanyaan: {query}"""

    with client.messages.stream(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        for text in stream.text_stream:
            yield text


async def stream_chat(
    query: str,
    chunks: list[dict],
    history: list[dict] | None = None,
) -> AsyncIterator[str]:
    """Same as stream_completion, tapi dengan history untuk multi-turn."""
    client = get_anthropic_client()
    context = build_context(chunks)

    current_user_message = f"""Konteks (untuk menjawab pertanyaan terbaru):
{context}

Pertanyaan: {query}"""

    messages = (history or []) + [
        {"role": "user", "content": current_user_message}
    ]

    with client.messages.stream(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            yield text
```

**Catatan penting**: `client.messages.stream()` dari Anthropic SDK adalah **sync** context manager (blocking I/O). Karena dipanggil dari async generator di FastAPI, ini akan block event loop selama streaming kalau dijalankan langsung. Wrap iterasi sync stream dengan `asyncio.to_thread` per chunk, atau — lebih simple — jalankan seluruh blocking stream loop di thread terpisah dan kirim hasil ke async generator lewat `asyncio.Queue`. Detail implementasi ini diputuskan saat coding, bukan blocker untuk plan.

---

## Step 3: Endpoint Stream — Completion

**File**: `api/v1/completion.py`

**Time**: 10 min

```python
from fastapi.responses import StreamingResponse
from core.sse import sse_event
from services.llm import stream_completion

@router.post("/stream")
async def completion_stream(
    request: CompletionRequest,
    company_id: UUID = Depends(get_company_id),
    tenant_id: UUID = Depends(validate_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Same pipeline as POST /v1/completion, tapi response di-stream sebagai SSE."""

    if not request.query.strip():
        raise HTTPException(status_code=400, detail={"error": "empty_query", "message": "Query cannot be empty"})

    chunks = await retrieve_chunks(query=request.query, company_id=company_id, tenant_id=tenant_id, session=session)

    if not chunks:
        raise HTTPException(status_code=404, detail={"error": "no_context", "message": "No relevant documents found in knowledge base"})

    sources = [
        {"document_id": str(c["document_id"]), "chunk_index": c["chunk_index"]}
        for c in chunks
    ]

    async def event_generator():
        try:
            async for text in stream_completion(request.query, chunks):
                yield sse_event({"text": text})
            yield sse_event({"sources": sources}, event="done")
        except Exception as e:
            yield sse_event({"error": "completion_error", "message": str(e)}, event="error")

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

Validasi `query` kosong & retrieval (404 no context) tetap dilakukan **sebelum** `StreamingResponse` dikembalikan — di titik ini header belum terkirim, jadi `HTTPException` masih valid. Begitu masuk `event_generator()`, error harus di-encode sebagai SSE `error` event (lihat Step 1), karena header sudah terkirim duluan dan status code tidak bisa diubah lagi.

---

## Step 4: Endpoint Stream — Chat

**File**: `api/v1/chat.py`

**Time**: 10 min

Pola sama dengan completion, plus: save `user` message di awal (sebelum stream mulai) dan `assistant` message di akhir generator setelah full text terkumpul.

```python
from fastapi.responses import StreamingResponse
from core.sse import sse_event
from services.llm import stream_chat

@router.post("/{conversation_id}/message/stream")
async def send_message_stream(
    conversation_id: UUID,
    request: MessageRequest,
    company_id: UUID = Depends(get_company_id),
    tenant_id: UUID = Depends(validate_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Same pipeline as POST /v1/chat/{id}/message, tapi response di-stream sebagai SSE."""

    if not request.message.strip():
        raise HTTPException(status_code=400, detail={"error": "empty_message", "message": "Message cannot be empty"})

    # validasi conversation, retrieval chunks, fetch history -> sama seperti send_message existing

    async def event_generator():
        full_text = ""
        try:
            async for text in stream_chat(request.message, chunks, history=history):
                full_text += text
                yield sse_event({"text": text})

            # simpan ke DB setelah stream selesai sukses
            session.add_all([
                Messages(conversation_id=conversation_id, role="user", content=request.message),
                Messages(conversation_id=conversation_id, role="assistant", content=full_text),
            ])
            await session.commit()

            yield sse_event({"sources": sources, "conversation_id": str(conversation_id)}, event="done")
        except Exception as e:
            yield sse_event({"error": "completion_error", "message": str(e)}, event="error")

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**Catatan**: kalau stream gagal di tengah jalan (exception sebelum `session.commit()`), user message tidak ikut tersimpan — supaya history tidak punya user message tanpa pasangan assistant response. Ini behavior yang disengaja, bukan bug.

---

## Step 5: Manual Testing

**Time**: 5 min

Test dengan `curl -N` (no buffering) untuk lihat stream realtime:

```bash
curl -N -X POST http://localhost:8000/v1/completion/stream \
  -H "X-Company-ID: <uuid>" \
  -H "X-Tenant-ID: <uuid>" \
  -H "Content-Type: application/json" \
  -d '{"query": "Apa kebijakan cuti tahunan?"}'
```

Expected output: beberapa baris `data: {"text": "..."}` muncul bertahap (bukan sekali muncul semua), diikuti `event: done` di akhir dengan payload `sources`.

Test juga error path: query kosong (400 sebelum stream mulai), tenant tidak valid (403/404 sebelum stream mulai), dan kalau memungkinkan simulasikan error setelah stream mulai (misal cabut API key sementara) untuk verifikasi `event: error` muncul dengan benar.

---

## Out of Scope (untuk phase ini)

- **Socket.IO/WebSocket** — tidak dibutuhkan karena tidak ada kebutuhan bidirectional (presence, multi-device sync, server-initiated push). Kalau requirement ini muncul nanti, evaluasi ulang sebagai phase terpisah.
- **Reconnection/resume stream** — SSE punya `Last-Event-ID` native untuk resume, tapi tidak diimplementasikan dulu kecuali ada kebutuhan konkret.
- **Frontend client code** — plan ini hanya backend API. Konsumsi via `EventSource` (browser) atau `fetch` + `ReadableStream` di sisi client.
