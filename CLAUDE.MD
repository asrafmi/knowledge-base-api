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

**API Endpoints**
- ✅ Companies: POST/GET/GET{id}/PATCH/DELETE (semua tested)
- ✅ Tenants: POST/GET/GET{id}/PATCH/DELETE dengan multi-tenant validation (semua tested)
- ✅ Header validation (X-Company-ID, X-Tenant-ID) di core/dependencies.py
- ✅ Tenant ownership validation (memastikan tenant_id milik company_id)

**Code Quality**
- README.md created with full setup & API documentation
- Error handling implemented per spec
- Multi-tenant convention implemented

### 🔄 Next Phase

1. **Document Ingestion Pipeline** (P0)
   - Document table & schema
   - File upload handler (PDF, DOCX, TXT)
   - File parsing (pypdf, python-docx, unstructured)
   - Chunking dengan tiktoken (512 token, 50 overlap)
   - Voyage AI embedding batch
   - `POST /v1/knowledge/ingest` endpoint
   - `GET /v1/knowledge/documents` endpoint
   - `DELETE /v1/knowledge/documents/{id}` endpoint

2. **RAG Core** (P1)
   - Document chunks table & pgvector indexing (HNSW)
   - Voyage AI similarity search
   - Claude integration (RAG system prompt)
   - `POST /v1/completion` (one-shot) endpoint
   - `POST /v1/chat` (create conversation) endpoint
   - `POST /v1/chat/{id}/message` (multi-turn) endpoint
   - `GET /v1/chat/{id}/history` endpoint

3. **Testing & Docs** (P2)
   - Unit tests for services
   - Integration tests for endpoints
   - API documentation
   - Deployment guide

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12+, FastAPI (async) |
| Database | PostgreSQL 16+ dengan ekstensi pgvector |
| ORM | SQLAlchemy 2.0 (async) + asyncpg |
| Embedding | Voyage AI API (`voyage-3` atau `voyage-3-lite`) |
| LLM | Anthropic Claude (`claude-sonnet-4-5`) |
| Doc parsing | `pypdf`, `python-docx`, `unstructured` |
| Chunking | Fixed-size, 512 token per chunk, 50 token overlap |
| Migration | Alembic |
| Validation | Pydantic v2 |
| Config | `pydantic-settings`, `.env` file |

---

## Project Structure

```
app/
├── main.py
├── core/
│   ├── config.py
│   └── dependencies.py
├── api/
│   └── v1/
│       ├── router.py
│       ├── knowledge.py
│       ├── completion.py
│       └── chat.py
├── services/
│   ├── embedding.py
│   ├── retrieval.py
│   ├── llm.py
│   └── ingestion.py
├── models/
│   ├── database.py
│   └── schemas.py
└── db/
    └── session.py
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
    content_type TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    chunk_index INT NOT NULL,
    embedding vector(1024),
    metadata JSONB DEFAULT '{}'
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

## Notes untuk Claude Code

- Semua database operation harus async (gunakan `AsyncSession` dari SQLAlchemy)
- Embedding Voyage AI: gunakan input_type `"query"` untuk query user, `"document"` untuk chunks saat ingestion — ini mempengaruhi kualitas retrieval
- Jangan hardcode `company_id` atau `tenant_id` di mana pun — selalu ambil dari header via dependency
- Untuk file parsing, handle exception per file type — jangan biarkan satu file yang corrupt crash seluruh request
- Vector dimension `1024` sesuai dengan model `voyage-3`. Kalau ganti model, sesuaikan dimensi di schema