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
- ✅ LLM integration (infrastructure/llm/anthropic/index.py): Claude integration, context building, RAG system prompt
- ✅ Pydantic schemas: CompletionRequest/Response, ChatCreate/Message/History schemas, SourceChunk
- ✅ Completion endpoint: POST `/v1/completion` one-shot RAG query
- ✅ Chat endpoints:
  - POST `/v1/chat` — create conversation
  - POST `/v1/chat/{id}/message` — multi-turn chat dengan full history
  - GET `/v1/chat/{id}/history` — fetch conversation history
- ✅ Router registration

**Phase 3: Streaming & Conversation List** ✅
- ✅ SSE helper (core/sse.py): format Server-Sent Events
- ✅ Streaming completion: POST `/v1/completion/stream` — token-by-token via SSE
- ✅ Streaming chat: POST `/v1/chat/{id}/message/stream` — token-by-token via SSE, save message setelah stream selesai
- ✅ Conversation listing: GET `/v1/conversation` — list semua conversation per tenant

**Phase 4: Layered Architecture Refactor (2026-07-08)** ✅
- ✅ Restrukturisasi seluruh source code ke dalam `src/` dengan 3 layer: **controller → service → repository** (pola ala NestJS)
- ✅ Repository per entity/tabel: `companies`, `tenants`, `documents`, `document_chunks`, `conversations`, `messages` — semua akses DB (`session.execute/add/delete`) hanya boleh ada di layer ini
- ✅ Service layer murni business logic, orkestrasi antar repository, tidak pernah akses DB langsung
- ✅ Controller hanya menerima `Depends` dari FastAPI dan meneruskan `session` sebagai parameter biasa ke service — root cause bug lama: `Depends()` FastAPI hanya di-resolve pada fungsi yang dipanggil FastAPI sendiri (route handler & dependency chain), bukan pada pemanggilan manual antar layer
- ✅ Fixed bug: `Documents(metadata=...)` seharusnya `meta=...` (kolom SQLAlchemy bernama `meta`, bukan `metadata`)

**Phase 5: Per-Tenant LLM Provider Settings (2026-07-09)** ✅
- ✅ Database migration (004_tenant_llm_settings.py): tabel `tenant_llm_settings`, 1:1 dengan tenant
- ✅ ORM model `TenantLLMSettings` di `models/database.py`, relationship `uselist=False` dari `Tenant`
- ✅ Enkripsi API key: `core/crypto.py` pakai Fernet symmetric encryption (`LLM_SETTINGS_ENCRYPTION_KEY` env var)
- ✅ Provider abstraction di `infrastructure/llm/`:
  - `base.py` — abstract `LLMProvider` (method `query()` & `stream()`), `DEFAULT_SYSTEM_PROMPT`, `RAG_GUARDRAIL_PROMPT` (selalu ditempel, tidak bisa dioverride tenant), `PROVIDER_MODELS` whitelist, `build_context()` (provider-agnostic)
  - `factory.py` — `get_llm_provider(provider, api_key)`, fallback ke API key kita sendiri kalau tenant tidak provide
  - `anthropic/index.py`, `openai/index.py`, `gemini/index.py` — masing-masing implement `LLMProvider`
- ✅ Repository (`repository/tenant_llm_settings.py`) & service (`services/tenant_llm_settings.py`): `get_settings_service`, `update_settings_service` (validasi provider/model terhadap whitelist), `resolve_llm_config_service` (dipakai chat & completion sebelum manggil LLM)
- ✅ Endpoint baru:
  - `GET /v1/llm-settings` — lihat setting tenant (tidak pernah return API key mentah/terenkripsi)
  - `PUT /v1/llm-settings` — set provider, model, API key (opsional), system prompt custom
- ✅ `services/chat.py` & `controller/v1/completion.py` di-wire ulang: sebelum manggil LLM, resolve dulu provider/model/prompt tenant via `resolve_llm_config_service`, ketimbang hardcode Anthropic

**Phase 5.1: Ollama (Self-Hosted) Provider (2026-07-10)** ✅
- ✅ Database migration (005_add_base_url.py): kolom `base_url` (nullable) di `tenant_llm_settings`, untuk provider self-hosted yang butuh alamat server, bukan API key
- ✅ `infrastructure/llm/ollama/index.py` — `OllamaProvider`, pakai `httpx` langsung ke REST API Ollama (`POST {base_url}/api/chat`), tidak ada dependency SDK tambahan. Streaming di-parse dari newline-delimited JSON (format asli Ollama, bukan SSE)
- ✅ `factory.get_llm_provider()` cabang khusus untuk `ollama`: tidak pernah mencari API key, langsung resolve `base_url` (fallback ke `DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"` kalau tenant tidak isi)
- ✅ `PROVIDER_MODELS["ollama"] = []` — model utk provider ini **tidak divalidasi** terhadap whitelist (berbeda dari anthropic/openai/gemini), karena tergantung model apa yang di-`pull` tenant di server Ollama mereka sendiri
- ✅ `LLMSettingsUpdate`/`LLMSettingsResponse` (`models/schemas.py`) + `upsert_repo` (`repository/tenant_llm_settings.py`) diperluas dengan field `base_url`

### 🔄 Next Phase

**Phase 6: Testing & Docs** (P2)
- Unit tests untuk services (retrieval, llm, ingestion) & repository layer
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
| LLM | Multi-provider per tenant: Anthropic Claude, OpenAI, Google Gemini, atau Ollama self-hosted (default: `claude-haiku-4-5`, fallback ke API key kita sendiri — Ollama tidak butuh API key sama sekali) |
| Secrets | `cryptography` (Fernet) untuk enkripsi API key tenant di DB |
| Doc parsing | `pypdf` (PDF), `python-docx` (DOCX), native (TXT) |
| Chunking | Fixed-size, 512 token per chunk, 50 token overlap (tiktoken) |
| Vector Search | pgvector with HNSW indexing (cosine similarity) |
| Migration | Alembic with automatic model detection |
| Validation | Pydantic v2 |
| Config | `pydantic-settings`, `.env` file |
| Docker | Multi-stage build, 3 services (postgres, migrator, app) |

---

## Project Structure

Seluruh source code ada di `src/`, dipisah 3 layer ala NestJS: **controller → service → repository**.

- **Controller** (`src/controller/v1/`): terima request, resolve `Depends` (session, header validation), lalu oper ke service sebagai argumen biasa. Tidak ada query DB langsung di sini.
- **Service** (`src/services/`): business logic, orkestrasi antar repository (dan antar service lain, misal `chat.py` memanggil `retrieval.py` & `llm.py`). Tidak pernah panggil `session.execute/add/delete` langsung.
- **Repository** (`src/repository/`): satu file per entity/tabel. Semua akses DB wajib ada di sini saja.

**Kenapa dipisah begini:** `Depends()` FastAPI hanya di-resolve pada fungsi yang dipanggil FastAPI sendiri (route handler & dependency chain-nya lewat `Depends`). Kalau dipanggil manual sebagai plain function call antar layer (service memanggil repository, dst), `Depends(get_session)` tidak pernah ter-resolve — parameter `session` akan terisi objek `Depends` mentah, bukan `AsyncSession`, dan akan error `AttributeError` saat dipakai untuk query. Solusinya: `Depends` cuma boleh dipakai di controller (dan `core/dependencies.py`, karena itu FastAPI dependency chain juga). Service dan repository menerima `session` sebagai parameter wajib biasa tanpa default `Depends`.

```
.
├── main.py                                  # FastAPI app entry point
├── alembic.ini                              # Alembic config (root, path ke src/alembic)
├── src/
│   ├── controller/v1/
│   │   ├── router.py                       # Main router aggregator
│   │   ├── companies.py                    # Company endpoints ✅
│   │   ├── tenants.py                      # Tenant endpoints ✅
│   │   ├── knowledge.py                    # Ingestion endpoints (3 routes) ✅
│   │   ├── completion.py                   # One-shot RAG + streaming endpoint ✅
│   │   ├── chat.py                         # Multi-turn chat endpoints (4 routes, termasuk stream) ✅
│   │   ├── conversation.py                 # List conversations per tenant ✅
│   │   └── llm_settings.py                 # GET/PUT tenant LLM provider settings ✅
│   ├── services/
│   │   ├── companies.py                    # Company business logic ✅
│   │   ├── tenants.py                      # Tenant business logic ✅
│   │   ├── knowledge.py                    # Ingestion pipeline orchestration ✅
│   │   ├── chat.py                         # Chat & conversation business logic ✅
│   │   ├── tenant_llm_settings.py          # LLM settings CRUD + resolve_llm_config_service ✅
│   │   ├── ingestion.py                    # File parsing & chunking ✅
│   │   └── retrieval.py                    # Vector similarity search (delegasi ke repository) ✅
│   ├── repository/
│   │   ├── companies.py                    # Query tabel companies ✅
│   │   ├── tenants.py                      # Query tabel tenants ✅
│   │   ├── documents.py                    # Query tabel documents ✅
│   │   ├── document_chunks.py              # Query tabel document_chunks + similarity search ✅
│   │   ├── conversations.py                # Query tabel conversations ✅
│   │   ├── messages.py                     # Query tabel messages ✅
│   │   └── tenant_llm_settings.py          # Query tabel tenant_llm_settings ✅
│   ├── core/
│   │   ├── config.py                       # Pydantic settings & env vars
│   │   ├── dependencies.py                 # FastAPI dependency injection (header + tenant validation)
│   │   ├── crypto.py                       # Enkripsi/dekripsi API key tenant (Fernet) ✅
│   │   └── sse.py                          # SSE event formatting helper
│   ├── infrastructure/
│   │   ├── voyage/
│   │   │   └── index.py                    # Voyage AI embedding client
│   │   └── llm/
│   │       ├── base.py                     # LLMProvider ABC, guardrail prompt, model whitelist ✅
│   │       ├── factory.py                  # get_llm_provider(provider, api_key, base_url) ✅
│   │       ├── anthropic/index.py          # AnthropicProvider ✅
│   │       ├── openai/index.py             # OpenAIProvider ✅
│   │       ├── gemini/index.py             # GeminiProvider ✅
│   │       └── ollama/index.py             # OllamaProvider (self-hosted, httpx, no API key) ✅
│   ├── models/
│   │   ├── database.py                     # SQLAlchemy ORM models
│   │   └── schemas.py                      # Pydantic request/response schemas
│   ├── db/
│   │   └── session.py                      # AsyncSession factory
│   └── alembic/                            # Database migrations
│       ├── versions/
│       │   ├── 001_initial_schema.py      # Companies & tenants ✅
│       │   ├── 002_documents_schema.py    # Documents & chunks ✅
│       │   ├── 003_add_conversations.py   # Conversations & messages ✅
│       │   ├── 004_tenant_llm_settings.py # Tenant LLM provider settings ✅
│       │   └── 005_add_base_url.py        # base_url column untuk provider self-hosted (Ollama) ✅
│       └── env.py                          # Migration environment config
├── misc/docker/
│   ├── docker-compose.yml                 # 3 services: postgres, migrator, app
│   └── Dockerfile                          # Multi-stage Python build
├── docs/                                    # Catatan implementasi per phase
├── .env                                     # Environment variables (local)
├── .env.example                              # Environment template
├── requirements.txt                        # Python dependencies
└── README.md                                # Setup & API documentation
```

---

## Environment Variables

```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dbname
ANTHROPIC_API_KEY=sk-ant-...
VOYAGE_API_KEY=pa-...
OPENAI_API_KEY=sk-...          # opsional — fallback default kalau tenant tidak provide API key sendiri
GEMINI_API_KEY=...             # opsional — fallback default kalau tenant tidak provide API key sendiri
LLM_SETTINGS_ENCRYPTION_KEY=... # wajib — Fernet key, generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
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

-- 1:1 dengan tenant — provider/model/api_key/system_prompt custom per tenant
CREATE TABLE tenant_llm_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL UNIQUE REFERENCES tenants(id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    provider VARCHAR(20) NOT NULL DEFAULT 'anthropic',
    model VARCHAR(100) NOT NULL DEFAULT 'claude-haiku-4-5',
    api_key_encrypted TEXT,   -- NULL = pakai API key kita sendiri (fallback). Tidak dipakai untuk provider 'ollama'
    base_url VARCHAR(255),    -- Khusus provider 'ollama' (self-hosted); NULL = fallback ke http://localhost:11434
    system_prompt TEXT,      -- NULL = pakai DEFAULT_SYSTEM_PROMPT
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
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

### LLM Settings — Per-Tenant Provider Configuration

Tenant bisa memilih provider LLM (Anthropic/OpenAI/Gemini/Ollama), model, API key sendiri (opsional untuk provider cloud, tidak dipakai sama sekali untuk Ollama), dan system prompt custom. Setting berlaku untuk semua endpoint RAG (`/v1/completion`, `/v1/chat/*`) dalam tenant itu — tidak ada override per-request.

#### `GET /v1/llm-settings`

Lihat setting LLM tenant saat ini. Kalau belum pernah di-set, return default (`anthropic` / `claude-haiku-4-5` / tanpa custom prompt).

- **Headers:** `X-Company-ID`, `X-Tenant-ID`
- **Response:**
```json
{
  "provider": "anthropic",
  "model": "claude-haiku-4-5",
  "has_custom_api_key": false,
  "base_url": null,
  "system_prompt": null,
  "updated_at": null
}
```
**Catatan:** API key (mentah maupun terenkripsi) **tidak pernah** dikembalikan di response — hanya flag boolean `has_custom_api_key`.

#### `PUT /v1/llm-settings`

Set atau update konfigurasi LLM tenant.

- **Headers:** `X-Company-ID`, `X-Tenant-ID`
- **Request (provider cloud, mis. OpenAI):**
```json
{
  "provider": "openai",
  "model": "gpt-5.1",
  "api_key": "sk-...",
  "system_prompt": "Kamu adalah asisten HR yang ramah."
}
```
- **Request (provider Ollama, self-hosted):**
```json
{
  "provider": "ollama",
  "model": "llama3.2",
  "base_url": "http://my-ollama-server:11434",
  "system_prompt": "Kamu adalah asisten HR yang ramah."
}
```
- `api_key`: opsional, **hanya relevan untuk `anthropic`/`openai`/`gemini`**. Kalau `null`/tidak diisi, fallback ke API key kita sendiri untuk provider tersebut. Diabaikan sepenuhnya untuk `provider: "ollama"`.
- `base_url`: opsional, **hanya relevan untuk `provider: "ollama"`**. Alamat server Ollama tenant. Kalau `null`/tidak diisi, fallback ke `http://localhost:11434`. Diabaikan untuk provider cloud lain.
- `system_prompt`: opsional, custom persona/gaya bahasa. **RAG guardrail (jawab hanya dari konteks, jangan mengarang) selalu ditempel otomatis di belakang prompt custom ini** — tidak bisa dioverride tenant.
- Validasi: `provider` harus salah satu dari `anthropic`/`openai`/`gemini`/`ollama`. Untuk `anthropic`/`openai`/`gemini`, `model` harus ada di whitelist provider tersebut (lihat `PROVIDER_MODELS` di `infrastructure/llm/base.py`) — 400 error kalau tidak valid. Untuk `ollama`, `model` **tidak divalidasi** (`PROVIDER_MODELS["ollama"] = []` menandakan skip whitelist) karena tergantung model apa yang di-`pull` tenant di server mereka sendiri.

---

## RAG Prompt & Multi-Provider LLM

Sejak Phase 5, LLM tidak lagi hardcoded ke Anthropic. Semua provider (`infrastructure/llm/anthropic|openai|gemini|ollama/index.py`) implement interface `LLMProvider` di `infrastructure/llm/base.py`:

```python
class LLMProvider(ABC):
    def query(self, system_prompt: str, messages: list[dict], model: str) -> str: ...
    def stream(self, system_prompt: str, messages: list[dict], model: str) -> AsyncIterator[str]: ...
```

`infrastructure/llm/base.py` juga jadi tempat konstanta bersama, dipakai semua provider:

```python
DEFAULT_SYSTEM_PROMPT = """Kamu adalah asisten yang menjawab pertanyaan berdasarkan dokumen yang tersedia.

Jawab dalam bahasa yang sama dengan pertanyaan pengguna, jika bahasa inggris, jawab dalam bahasa inggris, jika bahasa indonesia, jawab dalam bahasa indonesia."""

RAG_GUARDRAIL_PROMPT = """Aturan wajib (tidak bisa diubah):
- Jawab hanya berdasarkan konteks yang diberikan
- Jika informasi tidak ada dalam konteks, katakan dengan jelas bahwa kamu tidak menemukan informasi tersebut
- Jangan mengarang jawaban"""

def build_context(chunks: list[dict]) -> str:
    return "\n\n".join(
        f"[Sumber {i+1} — {c.get('meta', {}).get('filename', 'unknown')}]\n{c['chunk_text']}"
        for i, c in enumerate(chunks)
    )
```

Final system prompt yang dikirim ke LLM = `(tenant.system_prompt or DEFAULT_SYSTEM_PROMPT) + "\n\n" + RAG_GUARDRAIL_PROMPT` — dibangun di `services/tenant_llm_settings.py::resolve_llm_config_service()`. Setiap pemanggilan LLM di `services/chat.py` dan `controller/v1/completion.py` wajib resolve config ini dulu, baru panggil `provider.query()`/`provider.stream()` — jangan pernah import provider spesifik langsung.

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
- Column metadata: gunakan `meta` bukan `metadata` (reserved keyword di SQLAlchemy) — jangan konstruksi model dengan kwarg `metadata=`, wajib `meta=`
- Vector dimension: 1024 untuk `voyage-4`. Update schema jika ganti embedding model
- Relationships: gunakan `cascade="all, delete-orphan"` untuk Documents → DocumentChunks
- Migration: Alembic auto-detects SQLAlchemy models, handle async URL conversion (remove `+asyncpg` untuk migration)
- **Layering**: semua `session.execute/add/delete/add_all` wajib ada di `src/repository/<entity>.py`. Service dan controller tidak boleh query DB langsung — lihat penjelasan `Depends()` di section Project Structure

**Embedding & Retrieval**
- Voyage AI client: gunakan `@lru_cache` singleton pattern untuk reuse connection
- Input type: gunakan `"query"` untuk user queries, `"document"` untuk chunks saat ingestion
- Vector search: HNSW index pada kolom `embedding` dengan `vector_cosine_ops` + `cosine_distance()` dalam query, query aktualnya ada di `src/repository/document_chunks.py::search_by_similarity_repo`
- Multi-tenant filter: semua queries harus include `company_id` AND `tenant_id` filter
- embeddings return type: `list[list[float]]` untuk chunks, `list[float]` untuk single query
- **Async/Sync Bridging**: Voyage AI client synchronous → gunakan `asyncio.to_thread(embed_query, query)` di async context untuk prevent event loop blocking

**File Processing**
- Supported types: PDF (pypdf), DOCX (python-docx), TXT (native)
- Error handling: catch exceptions per file type, don't let one corrupt file crash request
- Temp files: save to `/tmp` via `save_upload_file()`, cleanup setelah selesai di finally block
- Chunking: fixed-size 512 token per chunk, 50 token overlap, gunakan tiktoken `cl100k_base`
- Pipeline orchestration (validasi file, parse, chunk, embed, simpan) ada di `src/services/knowledge.py`, dipanggil dari `src/controller/v1/knowledge.py`

**API & Dependencies**
- Headers: `X-Company-ID` dan `X-Tenant-ID` mandatory di semua knowledge endpoints
- Validation: `get_company_id()` extracts header, `validate_tenant()` checks ownership (query tenant lookup didelegasikan ke `src/repository/tenants.py`)
- Error format: return `{"error": "code", "message": "detail"}` untuk consistency
- Router aggregation: register semua router di `src/controller/v1/router.py`

**RAG & Chat**
- Retrieval: `retrieve_chunks()` di `src/services/retrieval.py`, returns list of dicts dengan `document_id`, `chunk_index`, `chunk_text`, `meta` — query similarity search-nya sendiri ada di `src/repository/document_chunks.py`
- Context building: `build_context()` di `src/infrastructure/llm/base.py`, provider-agnostic, concatenates chunks dengan source formatting
- LLM calls: tidak ada lagi `query_completion()`/`query_chat()` global. Setiap tempat yang butuh jawaban LLM wajib panggil `resolve_llm_config_service(tenant_id, session)` dulu (dari `src/services/tenant_llm_settings.py`) untuk dapat `(provider_instance, model, system_prompt)`, baru panggil `provider.query(system_prompt, messages, model)` (one-shot) atau `provider.stream(...)` (SSE)
- Provider resolution: `get_llm_provider(provider, api_key, base_url)` di `src/infrastructure/llm/factory.py` — untuk provider cloud (anthropic/openai/gemini), `api_key=None` fallback ke API key kita sendiri (`settings.anthropic_api_key` / `openai_api_key` / `gemini_api_key`); untuk `provider="ollama"`, `api_key` diabaikan sepenuhnya dan `base_url=None` fallback ke `DEFAULT_OLLAMA_BASE_URL` (`http://localhost:11434`)
- Ollama: self-hosted, tanpa API key. `OllamaProvider` (`src/infrastructure/llm/ollama/index.py`) pakai `httpx` langsung ke `POST {base_url}/api/chat` — tidak ada SDK tambahan. Response stream Ollama berupa newline-delimited JSON (bukan SSE), di-parse baris per baris
- System prompt: `(tenant.system_prompt or DEFAULT_SYSTEM_PROMPT) + RAG_GUARDRAIL_PROMPT`, guardrail selalu ditempel tidak bisa dioverride tenant — lihat section "RAG Prompt & Multi-Provider LLM"
- Chat & conversation business logic (create, send message, get history, list conversations, streaming) ada di `src/services/chat.py`
- Chat history: loaded via `src/repository/messages.py`, ordered by `created_at`, passed sebagai `messages` array ke provider (dinormalisasi `{"role", "content"}`, tiap provider adapt ke format SDK masing-masing)
- SSE streaming: format event pakai `sse_event()` di `src/core/sse.py`, dipakai di endpoint `/v1/completion/stream` dan `/v1/chat/{id}/message/stream`
- API key tenant disimpan terenkripsi (`api_key_encrypted` kolom, Fernet via `src/core/crypto.py`), didekripsi on-the-fly di `resolve_llm_config_service()` — **tidak pernah** dikembalikan mentah/terenkripsi lewat API response manapun

**Docker Deployment**
- 3 services: postgres (pgvector/pgvector:pg16), migrator (runs alembic), app (uvicorn)
- Service dependencies: app waits for migrator completion, migrator waits for postgres health
- All env vars loaded from `.env` file via docker-compose substitution
- Volumes: postgres_data untuk persistence, app code mounted for development
- Docker Compose v2: removed deprecated `version:` attribute