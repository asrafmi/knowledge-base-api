# Knowledge Base API — Build Spec

## Overview

REST API untuk knowledge base dengan RAG pipeline dan multi-turn chat. Dibangun dengan FastAPI + PostgreSQL (pgvector) + Claude (Anthropic) + Voyage AI untuk embedding.

## Progress

### ✅ Completed

**Infrastructure & Setup (2026-06-01)**
- Project structure initialized (root folder)
- requirements.txt dengan all dependencies
- .env & .env.example setup
- Virtual environment (.venv) setup
- Alembic database migration system configured
- PostgreSQL 16 running via docker-compose (misc/docker/docker-compose.yml)
- Migrations applied successfully (001_initial_schema.py)

**Database**
- companies table — created & tested
- tenants table — created & tested
- Multi-tenant relationship setup dengan ON DELETE CASCADE

**API Endpoints (Phase 0)**
- ✅ Companies: POST/GET/GET{id}/PATCH/DELETE (semua tested)
- ✅ Tenants: POST/GET/GET{id}/PATCH/DELETE dengan multi-tenant validation (semua tested)
- ✅ Header validation (X-Company-ID, X-Tenant-ID) di core/dependencies.py
- ✅ Tenant ownership validation (memastikan tenant_id milik company_id)

**Code Quality**
- README.md created with full setup & API documentation
- Error handling implemented per spec
- Multi-tenant convention implemented

**Phase 1: Document Ingestion Pipeline (2026-06-27)** ✅
- ✅ Database migration (002_documents_schema.py): documents & document_chunks tables dengan pgvector
- ✅ ORM models (models/database.py): Document & DocumentChunks dengan relationships & cascade delete
- ✅ Pydantic schemas (models/schemas.py): DocumentResponse, DocumentItemResponse, DocumentListResponse, IngestionResponse
- ✅ Ingestion service (services/ingestion.py): file parsing, chunking dengan tiktoken (512 token, 50 overlap)
- ✅ Embedding service (infrastructure/voyage/index.py): Voyage AI client singleton, embed_chunks & embed_query functions
- ✅ Knowledge router (api/v1/knowledge.py): 3 endpoints implemented & tested
  - POST `/v1/knowledge/ingest` — upload & process dokumen
  - GET `/v1/knowledge/documents` — list dokumen per tenant
  - DELETE `/v1/knowledge/documents/{id}` — delete dokumen dengan cascade

**Phase 2: RAG Core** (2026-06-27) ✅
- ✅ Database migration (003_add_conversations.py): conversations & messages tables
- ✅ ORM models: Conversations & Messages dengan relationships
- ✅ Retrieval service (services/retrieval.py): pgvector cosine_distance search
- ✅ LLM service (services/llm.py): Claude integration, context building, RAG system prompt
- ✅ Pydantic schemas: CompletionRequest/Response, ChatCreate/Message/History schemas, SourceChunk
- ✅ Completion endpoint (api/v1/completion.py): POST `/v1/completion` one-shot RAG query
- ✅ Chat endpoints (api/v1/chat.py):
  - POST `/v1/chat` — create conversation
  - POST `/v1/chat/{id}/message` — multi-turn chat dengan full history
  - GET `/v1/chat/{id}/history` — fetch conversation history
- ✅ Router registration di api/v1/router.py

### 🔄 Next Phase

**Phase 3: Testing & Docs** (P2)
- Unit tests untuk services (retrieval, llm, ingestion)
- Integration tests untuk endpoints
- API documentation expansion (OpenAPI/Swagger)
- Deployment guide & production checklist

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI (async) |
| Database | PostgreSQL 16 + pgvector extension |
| ORM | SQLAlchemy 2.0 (async) + asyncpg |
| Embedding | Voyage AI API (`voyage-4`) |
| LLM | Anthropic Claude (`claude-haiku-4-5`) |
| Doc parsing | `pypdf` (PDF), `python-docx` (DOCX), native (TXT) |
| Chunking | Fixed-size, 512 token per chunk, 50 token overlap (tiktoken) |
| Vector Search | pgvector with HNSW indexing (cosine similarity) |
| Migration | Alembic with automatic model detection |
| Validation | Pydantic v2 |
| Config | `pydantic-settings`, `.env` file |
| Docker | Multi-stage build, 3 services (postgres, migrator, app) |

---

## Project Structure

```
.
├── main.py                                  # FastAPI app entry point
├── core/
│   ├── config.py                           # Pydantic settings & env vars
│   └── dependencies.py                     # FastAPI dependency injection
├── api/v1/
│   ├── router.py                           # Main router aggregator
│   ├── knowledge.py                        # Ingestion endpoints (3 routes) ✅
│   ├── completion.py                       # One-shot RAG endpoint ✅
│   └── chat.py                             # Multi-turn chat endpoints (3 routes) ✅
├── services/
│   ├── ingestion.py                        # File parsing & chunking ✅
│   ├── retrieval.py                        # Vector similarity search ✅
│   └── llm.py                              # Claude integration ✅
├── infrastructure/
│   └── voyage/
│       └── index.py                        # Voyage AI embedding client
├── models/
│   ├── database.py                         # SQLAlchemy ORM models
│   └── schemas.py                          # Pydantic request/response schemas
├── db/
│   └── session.py                          # AsyncSession factory
├── alembic/                                # Database migrations
│   ├── versions/
│   │   ├── 001_initial_schema.py          # Companies & tenants ✅
│   │   ├── 002_documents_schema.py        # Documents & chunks ✅
│   │   └── 003_add_conversations.py       # Conversations & messages ✅
│   └── env.py                              # Migration environment config
├── misc/docker/
│   ├── docker-compose.yml                 # 3 services: postgres, migrator, app
│   └── Dockerfile                          # Multi-stage Python build
├── .env                                    # Environment variables (local)
├── .env.example                            # Environment template
├── requirements.txt                        # Python dependencies
└── README.md                               # Setup & API documentation
```

---

## Environment Variables

```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dbname
ANTHROPIC_API_KEY=sk-ant-...
VOYAGE_API_KEY=pa-...
CHUNK_SIZE=512
CHUNK_OVERLAP=50
RETRIEVAL_TOP_K=5
```

---

## Database Schema

Buat semua tabel ini via Alembic migration. Aktifkan ekstensi pgvector sebelum membuat tabel.

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    content_type VARCHAR(50),
    meta JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    embedding vector(1024),
    meta JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ANN index untuk similarity search
CREATE INDEX ON document_chunks
    USING hnsw (embedding vector_cosine_ops);

-- Composite index untuk multi-tenant filter
CREATE INDEX ON document_chunks (company_id, tenant_id);

CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ON messages (conversation_id, created_at);
```

---

## Multi-Tenant Convention

Setiap request wajib membawa dua header berikut. Semua query ke database harus selalu difilter dengan kedua nilai ini — tidak ada pengecualian.

```
X-Company-ID: <uuid>
X-Tenant-ID: <uuid>
```

Validasi dilakukan di `core/dependencies.py` via FastAPI `Depends`. Tambahkan validasi bahwa `tenant_id` memang benar-benar milik `company_id` yang dikirim — query ke tabel `tenants` untuk konfirmasi.

---

## API Endpoints

### Knowledge — Ingestion

#### `POST /v1/knowledge/ingest`

Upload dan proses dokumen ke knowledge base.

- **Request:** `multipart/form-data`, field `file` (PDF, DOCX, atau TXT)
- **Headers:** `X-Company-ID`, `X-Tenant-ID`
- **Response:**
```json
{
  "document_id": "uuid",
  "filename": "report.pdf",
  "chunks_created": 24,
  "status": "success"
}
```

**Pipeline ingestion:**
1. Terima file upload
2. Parse teks dari file sesuai tipe (PDF → pypdf, DOCX → python-docx, TXT → langsung)
3. Chunking: fixed-size 512 token, overlap 50 token. Gunakan `tiktoken` untuk tokenisasi (`cl100k_base` encoding)
4. Embed semua chunks via Voyage AI API secara batch
5. Simpan record ke tabel `documents` lalu semua chunks ke `document_chunks`
6. Return summary

#### `GET /v1/knowledge/documents`

List semua dokumen milik tenant.

- **Headers:** `X-Company-ID`, `X-Tenant-ID`
- **Response:** array dokumen dengan `id`, `filename`, `chunk_count`, `created_at`

#### `DELETE /v1/knowledge/documents/{document_id}`

Hapus dokumen beserta semua chunks-nya. Karena ada `ON DELETE CASCADE`, cukup hapus record di tabel `documents`.

- **Headers:** `X-Company-ID`, `X-Tenant-ID`
- **Validasi:** pastikan `document_id` memang milik tenant yang bersangkutan sebelum hapus

---

### Completion — One-shot

#### `POST /v1/completion`

Query langsung tanpa menyimpan history.

- **Headers:** `X-Company-ID`, `X-Tenant-ID`
- **Request:**
```json
{
  "query": "Apa kebijakan cuti tahunan?"
}
```
- **Response:**
```json
{
  "answer": "...",
  "sources": [
    { "document_id": "uuid", "filename": "hr-policy.pdf", "chunk_index": 3 }
  ]
}
```

**Pipeline:**
1. Embed query via Voyage AI
2. Similarity search di `document_chunks` dengan filter `company_id` + `tenant_id`, ambil top 5
3. Build context string dari chunks
4. Kirim ke Claude dengan system prompt RAG
5. Return jawaban + sources

---

### Chat — Multi-turn

#### `POST /v1/chat`

Buat conversation baru.

- **Headers:** `X-Company-ID`, `X-Tenant-ID`
- **Request:**
```json
{
  "user_id": "user-123"
}
```
- **Response:**
```json
{
  "conversation_id": "uuid",
  "created_at": "..."
}
```

#### `POST /v1/chat/{conversation_id}/message`

Kirim pesan dan dapatkan respons. History conversation otomatis disertakan ke Claude.

- **Headers:** `X-Company-ID`, `X-Tenant-ID`
- **Request:**
```json
{
  "message": "Boleh ambil cuti berapa hari?"
}
```
- **Response:**
```json
{
  "conversation_id": "uuid",
  "answer": "...",
  "sources": [...]
}
```

**Pipeline:**
1. Validasi `conversation_id` milik tenant ini
2. Embed query
3. Similarity search dengan filter tenant
4. Ambil semua messages dari conversation ini, urutkan by `created_at ASC`
5. Build messages array untuk Claude: history lama + user message baru (dengan context RAG di-inject ke user message terakhir)
6. Kirim ke Claude
7. Simpan user message + assistant response ke tabel `messages`
8. Return response

#### `GET /v1/chat/{conversation_id}/history`

Ambil semua pesan dalam sebuah conversation.

- **Headers:** `X-Company-ID`, `X-Tenant-ID`
- **Response:** array messages dengan `role`, `content`, `created_at`

---

## RAG Prompt Template

Gunakan template ini di `services/llm.py`:

```python
SYSTEM_PROMPT = """Kamu adalah asisten yang menjawab pertanyaan berdasarkan dokumen yang tersedia.

Aturan:
- Jawab hanya berdasarkan konteks yang diberikan
- Jika informasi tidak ada dalam konteks, katakan dengan jelas bahwa kamu tidak menemukan informasi tersebut
- Jangan mengarang jawaban
- Jawab dalam bahasa yang sama dengan pertanyaan pengguna"""

def build_user_message(query: str, chunks: list[dict]) -> str:
    context = "\n\n".join(
        f"[Sumber {i+1} — {c['metadata'].get('filename', 'unknown')}]\n{c['chunk_text']}"
        for i, c in enumerate(chunks)
    )
    return f"""Konteks:\n{context}\n\nPertanyaan: {query}"""
```

---

## Chunking Implementation

Gunakan `tiktoken` untuk tokenisasi. Implementasi di `services/ingestion.py`:

```python
import tiktoken

def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = start + chunk_size
        chunk_tokens = tokens[start:end]
        chunks.append(enc.decode(chunk_tokens))
        start += chunk_size - overlap
    return chunks
```

---

## Error Handling Convention

Gunakan format error yang konsisten di semua endpoint:

```json
{
  "error": "tenant_not_found",
  "message": "Tenant ID tidak ditemukan atau tidak milik company ini",
  "status_code": 404
}
```

HTTP status codes:
- `400` — request tidak valid (file type tidak support, field kosong)
- `403` — akses ditolak (tenant bukan milik company)
- `404` — resource tidak ditemukan
- `422` — validation error Pydantic (default FastAPI)
- `500` — internal server error

---

## Implementation Notes

**Database & ORM**
- Semua database operation harus async (gunakan `AsyncSession` dari SQLAlchemy)
- Column metadata: gunakan `meta` bukan `metadata` (reserved keyword di SQLAlchemy)
- Vector dimension: 1024 untuk `voyage-4`. Update schema jika ganti embedding model
- Relationships: gunakan `cascade="all, delete-orphan"` untuk Documents → DocumentChunks
- Migration: Alembic auto-detects SQLAlchemy models, handle async URL conversion (remove `+asyncpg` untuk migration)

**Embedding & Retrieval**
- Voyage AI client: gunakan `@lru_cache` singleton pattern untuk reuse connection
- Input type: gunakan `"query"` untuk user queries, `"document"` untuk chunks saat ingestion
- Vector search: HNSW index pada kolom `embedding` dengan `vector_cosine_ops` + `cosine_distance()` dalam query
- Multi-tenant filter: semua queries harus include `company_id` AND `tenant_id` filter
- embeddings return type: `list[list[float]]` untuk chunks, `list[float]` untuk single query
- **Async/Sync Bridging**: Voyage AI client synchronous → gunakan `asyncio.to_thread(embed_query, query)` di async context untuk prevent event loop blocking

**File Processing**
- Supported types: PDF (pypdf), DOCX (python-docx), TXT (native)
- Error handling: catch exceptions per file type, don't let one corrupt file crash request
- Temp files: save to `/tmp` via `save_upload_file()`, cleanup setelah selesai di finally block
- Chunking: fixed-size 512 token per chunk, 50 token overlap, gunakan tiktoken `cl100k_base`

**API & Dependencies**
- Headers: `X-Company-ID` dan `X-Tenant-ID` mandatory di semua knowledge endpoints
- Validation: `get_company_id()` extracts header, `validate_tenant()` checks ownership
- Error format: return `{"error": "code", "message": "detail"}` untuk consistency
- Router aggregation: register knowledge router di `api/v1/router.py`

**RAG & Chat (Phase 2)**
- Retrieval: `retrieve_chunks()` di services/retrieval.py, returns list of dicts dengan `document_id`, `chunk_index`, `chunk_text`, `meta`
- Context building: `build_context()` di services/llm.py, concatenates chunks dengan source formatting
- One-shot: `query_completion()` untuk single query tanpa history
- Multi-turn: `query_chat()` untuk conversations dengan history context (messages array passed to Claude)
- System prompt: RAG template di SYSTEM_PROMPT constant, consistent across completion & chat
- Chat history: loaded from messages table, ordered by `created_at`, passed to Claude messages array

**Docker Deployment**
- 3 services: postgres (pgvector/pgvector:pg16), migrator (runs alembic), app (uvicorn)
- Service dependencies: app waits for migrator completion, migrator waits for postgres health
- All env vars loaded from `.env` file via docker-compose substitution
- Volumes: postgres_data untuk persistence, app code mounted for development
- Docker Compose v2: removed deprecated `version:` attribute