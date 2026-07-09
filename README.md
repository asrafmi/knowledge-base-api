# Knowledge Base API

REST API untuk knowledge base dengan RAG pipeline dan multi-turn chat. Dibangun dengan FastAPI + PostgreSQL (pgvector) + Voyage AI untuk embedding. LLM provider (Anthropic Claude, OpenAI, Google Gemini, atau Ollama self-hosted) dan model bisa dikonfigurasi per tenant.

## Quick Start

### Prerequisites
- Docker & Docker Compose
- (Optional) Python 3.11+ untuk local development

### Setup dengan Docker (Recommended)

1. **Setup Environment Variables**
```bash
cp .env.example .env
# Edit .env dengan API keys (ANTHROPIC_API_KEY, VOYAGE_API_KEY, opsional OPENAI_API_KEY/GEMINI_API_KEY)
# Generate LLM_SETTINGS_ENCRYPTION_KEY:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

2. **Build & Start**
```bash
cd misc/docker
docker-compose up --build
```

Ini akan:
- Build Docker image
- Start PostgreSQL
- Run migrator (install pgvector + run migrations)
- Start FastAPI server

Services:
- `postgres` — Database (port 5432)
- `migrator` — Run migrations then exit
- `app` — FastAPI server (port 8000)

Server running di `http://localhost:8000`
API docs: `http://localhost:8000/docs`

**After migrations complete:**
```bash
docker-compose logs migrator
```

**Stop:**
```bash
docker-compose down
```

**Run migrations only:**
```bash
docker-compose run migrator
```

**View logs:**
```bash
docker-compose logs -f app
docker-compose logs migrator
```

---

### Setup Local Development (tanpa Docker)

1. **Clone & Install Dependencies**
```bash
uv venv
source .venv/bin/activate  # atau .venv\Scripts\activate di Windows
pip install -r requirements.txt
```

2. **Setup Environment Variables**
```bash
cp .env.example .env
# Edit .env dengan database URL & API keys
```

3. **Start PostgreSQL Container Only**
```bash
cd misc/docker
docker-compose up postgres -d
```

4. **Setup Database**
```bash
# Install pgvector extension
psql -h localhost -U postgres -d knowledge_base -c "CREATE EXTENSION IF NOT EXISTS vector"

# Run migrations
alembic upgrade head
```

5. **Start Server**
```bash
uvicorn main:app --reload --port 8000
```

## API Endpoints

### Health Check
- `GET /health` — Server health status

### Companies
- `POST /v1/companies` — Create company
- `GET /v1/companies` — List all companies
- `GET /v1/companies/{company_id}` — Get company by ID
- `PATCH /v1/companies/{company_id}` — Update company
- `DELETE /v1/companies/{company_id}` — Delete company

### Tenants (Multi-tenant)
- `POST /v1/tenants` — Create tenant
  - **Headers:** `X-Company-ID`
- `GET /v1/tenants` — List tenants by company
  - **Headers:** `X-Company-ID`
- `GET /v1/tenants/{tenant_id}` — Get tenant
  - **Headers:** `X-Company-ID`
- `PATCH /v1/tenants/{tenant_id}` — Update tenant
  - **Headers:** `X-Company-ID`
- `DELETE /v1/tenants/{tenant_id}` — Delete tenant
  - **Headers:** `X-Company-ID`

### Knowledge Base — Document Ingestion
- `POST /v1/knowledge/ingest` — Upload & ingest document
  - **Headers:** `X-Company-ID`, `X-Tenant-ID`
  - **Content:** multipart/form-data, field `file` (PDF, DOCX, TXT)
  - **Response:** document_id, chunks_created
- `GET /v1/knowledge/documents` — List documents
  - **Headers:** `X-Company-ID`, `X-Tenant-ID`
  - **Response:** list of documents with chunk counts
- `DELETE /v1/knowledge/documents/{document_id}` — Delete document
  - **Headers:** `X-Company-ID`, `X-Tenant-ID`

### Completion — One-Shot RAG Query
- `POST /v1/completion` — Query knowledge base (no history)
  - **Headers:** `X-Company-ID`, `X-Tenant-ID`
  - **Body:** `{"query": "..."}`
  - **Response:** answer + source chunks
- `POST /v1/completion/stream` — Query knowledge base, stream answer token-by-token (SSE)
  - **Headers:** `X-Company-ID`, `X-Tenant-ID`
  - **Body:** `{"query": "..."}`
  - **Response:** `text/event-stream` — event `text` per token, event `done` berisi sources, event `error` jika gagal

### Chat — Multi-Turn Conversation
- `POST /v1/chat` — Create conversation
  - **Headers:** `X-Company-ID`, `X-Tenant-ID`
  - **Body:** `{"user_id": "..."}` (optional)
  - **Response:** conversation_id
- `POST /v1/chat/{conversation_id}/message` — Send message
  - **Headers:** `X-Company-ID`, `X-Tenant-ID`
  - **Body:** `{"message": "..."}`
  - **Response:** answer + source chunks
- `POST /v1/chat/{conversation_id}/message/stream` — Send message, stream answer token-by-token (SSE)
  - **Headers:** `X-Company-ID`, `X-Tenant-ID`
  - **Body:** `{"message": "..."}`
  - **Response:** `text/event-stream` — event `text` per token, event `done` berisi sources + conversation_id, event `error` jika gagal. Pesan disimpan ke DB hanya setelah stream selesai sukses.
- `GET /v1/chat/{conversation_id}/history` — Get conversation history
  - **Headers:** `X-Company-ID`, `X-Tenant-ID`
  - **Response:** list of all messages (user + assistant)

### Conversation — List
- `GET /v1/conversation` — List semua conversation milik tenant
  - **Headers:** `X-Company-ID`, `X-Tenant-ID`
  - **Response:** list of conversation_id + created_at

### LLM Settings — Per-Tenant Provider Configuration
Tenant bisa memilih provider LLM (`anthropic`/`openai`/`gemini`/`ollama`), model, API key sendiri (opsional — fallback ke API key kita kalau kosong), dan system prompt custom. Berlaku untuk semua endpoint RAG (`/v1/completion`, `/v1/chat/*`) dalam tenant tersebut.
- `GET /v1/llm-settings` — Lihat setting saat ini
  - **Headers:** `X-Company-ID`, `X-Tenant-ID`
  - **Response:** `provider`, `model`, `has_custom_api_key` (boolean, API key tidak pernah dikembalikan), `base_url`, `system_prompt`, `updated_at`
- `PUT /v1/llm-settings` — Set/update provider, model, API key, system prompt
  - **Headers:** `X-Company-ID`, `X-Tenant-ID`
  - **Body:** `{"provider": "openai", "model": "gpt-5.1", "api_key": "sk-...", "base_url": null, "system_prompt": "..."}` (`api_key`, `base_url`, `system_prompt` semuanya opsional)
  - **Validasi:** `provider` harus `anthropic`/`openai`/`gemini`/`ollama`. Untuk `anthropic`/`openai`/`gemini`, `model` harus ada di whitelist provider tersebut — 400 kalau tidak valid. Untuk `ollama`, `model` bebas (tidak divalidasi) karena tergantung model apa yang di-pull tenant di server mereka sendiri.
  - **Catatan:** system prompt custom selalu digabung dengan RAG guardrail wajib (jawab hanya dari konteks, jangan mengarang) yang tidak bisa di-override
  - **Ollama (self-hosted):** provider ini **tidak butuh API key**. Isi `base_url` dengan alamat server Ollama tenant (mis. `http://localhost:11434` atau URL server mereka); kalau tidak diisi, fallback ke `http://localhost:11434`.

**Multi-tenant Headers (Required for knowledge base endpoints):**
```
X-Company-ID: <uuid>
X-Tenant-ID: <uuid>
```

## Project Structure

Kode aplikasi berada di `src/`, mengikuti 3 layer ala NestJS: **controller → service → repository**.

- **Controller** — terima request, resolve dependency FastAPI (`Depends`), oper ke service sebagai argumen biasa
- **Service** — business logic, orkestrasi antar repository/service lain, tidak pernah akses DB langsung
- **Repository** — satu file per tabel, satu-satunya tempat yang boleh menjalankan query (`session.execute`, dll)

```
knowledge-base-api/
├── main.py                                  # FastAPI app entry point
├── alembic.ini                              # Alembic config (root, path ke src/alembic)
├── requirements.txt                          # Python dependencies
├── .env                                      # Environment variables (gitignored)
├── .env.example                              # Environment template
├── src/
│   ├── controller/v1/
│   │   ├── router.py                       # Main API router aggregator
│   │   ├── companies.py                    # Company endpoints
│   │   ├── tenants.py                      # Tenant endpoints
│   │   ├── knowledge.py                    # Document ingestion endpoints
│   │   ├── completion.py                   # One-shot RAG + streaming endpoint
│   │   ├── chat.py                         # Multi-turn chat endpoints (+ streaming)
│   │   ├── conversation.py                 # List conversations per tenant
│   │   └── llm_settings.py                 # GET/PUT tenant LLM provider settings
│   ├── services/
│   │   ├── companies.py                    # Company business logic
│   │   ├── tenants.py                      # Tenant business logic
│   │   ├── knowledge.py                    # Ingestion pipeline orchestration
│   │   ├── chat.py                         # Chat & conversation business logic
│   │   ├── tenant_llm_settings.py          # LLM settings CRUD + resolve_llm_config_service
│   │   ├── ingestion.py                    # Document parsing & chunking
│   │   └── retrieval.py                    # Vector similarity search (delegasi ke repository)
│   ├── repository/
│   │   ├── companies.py                    # Query tabel companies
│   │   ├── tenants.py                      # Query tabel tenants
│   │   ├── documents.py                    # Query tabel documents
│   │   ├── document_chunks.py              # Query tabel document_chunks + similarity search
│   │   ├── conversations.py                # Query tabel conversations
│   │   ├── messages.py                     # Query tabel messages
│   │   └── tenant_llm_settings.py          # Query tabel tenant_llm_settings
│   ├── core/
│   │   ├── config.py                       # Settings & environment variables
│   │   ├── dependencies.py                 # FastAPI dependencies & validation
│   │   ├── crypto.py                       # Enkripsi/dekripsi API key tenant (Fernet)
│   │   └── sse.py                          # SSE event formatting helper
│   ├── db/
│   │   └── session.py                      # AsyncSession & engine setup
│   ├── models/
│   │   ├── database.py                     # SQLAlchemy ORM models
│   │   └── schemas.py                      # Pydantic request/response schemas
│   ├── infrastructure/
│   │   ├── voyage/
│   │   │   └── index.py                    # Voyage AI embedding client
│   │   └── llm/
│   │       ├── base.py                     # LLMProvider ABC, guardrail prompt, model whitelist
│   │       ├── factory.py                  # get_llm_provider(provider, api_key, base_url)
│   │       ├── anthropic/index.py          # AnthropicProvider
│   │       ├── openai/index.py             # OpenAIProvider
│   │       ├── gemini/index.py             # GeminiProvider
│   │       └── ollama/index.py             # OllamaProvider (self-hosted, no API key, httpx-based)
│   └── alembic/                            # Database migrations
│       ├── env.py                          # Alembic configuration
│       ├── versions/                       # Migration files
│       └── script.py.mako                  # Migration template
├── docs/                                    # Catatan implementasi per phase
└── misc/docker/
    └── docker-compose.yml                  # PostgreSQL container
```

## Database Schema

### companies
```sql
id UUID PRIMARY KEY
name TEXT NOT NULL
created_at TIMESTAMPTZ
```

### tenants
```sql
id UUID PRIMARY KEY
company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE
name TEXT NOT NULL
created_at TIMESTAMPTZ
```

### documents
```sql
id UUID PRIMARY KEY
company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE
tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE
filename TEXT NOT NULL
content_type VARCHAR(50)
meta JSONB DEFAULT '{}'
created_at TIMESTAMPTZ
```

### document_chunks
```sql
id UUID PRIMARY KEY
document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE
company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE
tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE
chunk_text TEXT NOT NULL
chunk_index INTEGER NOT NULL
embedding vector(1024)
meta JSONB DEFAULT '{}'
created_at TIMESTAMPTZ
-- HNSW index: CREATE INDEX ON document_chunks USING hnsw (embedding vector_cosine_ops)
-- Composite index: CREATE INDEX ON document_chunks (company_id, tenant_id)
```

### conversations
```sql
id UUID PRIMARY KEY
company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE
tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE
user_id TEXT
created_at TIMESTAMPTZ
```

### messages
```sql
id UUID PRIMARY KEY
conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE
role TEXT NOT NULL CHECK (role IN ('user', 'assistant'))
content TEXT NOT NULL
created_at TIMESTAMPTZ
-- Index: CREATE INDEX ON messages (conversation_id, created_at)
```

### tenant_llm_settings
```sql
id UUID PRIMARY KEY
tenant_id UUID NOT NULL UNIQUE REFERENCES tenants(id) ON DELETE CASCADE
company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE
provider VARCHAR(20) NOT NULL DEFAULT 'anthropic'
model VARCHAR(100) NOT NULL DEFAULT 'claude-haiku-4-5'
api_key_encrypted TEXT          -- NULL = pakai API key kita sendiri (fallback). Tidak dipakai untuk provider 'ollama'
base_url VARCHAR(255)           -- Khusus provider 'ollama' (self-hosted); NULL = fallback ke http://localhost:11434
system_prompt TEXT              -- NULL = pakai default system prompt
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

## Multi-Tenant Convention

Semua request yang berhubungan dengan knowledge base **wajib membawa header**:

```
X-Company-ID: <uuid>   # Company yang mengakses
X-Tenant-ID: <uuid>    # Tenant dalam company tersebut (untuk validation)
```

Validasi dilakukan di `src/core/dependencies.py` (query tenant lookup-nya sendiri ada di `src/repository/tenants.py`):
- Memastikan `X-Company-ID` valid dan ada di database
- Memastikan `X-Tenant-ID` memang milik `X-Company-ID` (query ke tabel tenants)

**Tidak ada pengecualian** — semua database query harus difilter dengan kedua nilai ini.

## Development

### Create Migration
Ketika ada perubahan schema database:
```bash
alembic revision --autogenerate -m "Description of change"
alembic upgrade head
```

### Run Tests
```bash
pytest  # (TODO: test suite setup)
```

### Format & Lint
```bash
black .
ruff check . --fix
```

## Environment Variables

| Variable | Description | Example |
|---|---|---|
| `DATABASE_URL` | PostgreSQL async connection string | `postgresql+asyncpg://user:pass@localhost:5432/db` |
| `ANTHROPIC_API_KEY` | Claude API key (default fallback kalau tenant tidak provide sendiri) | `sk-ant-...` |
| `VOYAGE_API_KEY` | Voyage AI API key | `pa-...` |
| `OPENAI_API_KEY` | OpenAI API key (opsional, default fallback) | `sk-...` |
| `GEMINI_API_KEY` | Google Gemini API key (opsional, default fallback) | `...` |
| `LLM_SETTINGS_ENCRYPTION_KEY` | Fernet key untuk enkripsi API key tenant di DB (wajib) | generate: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `CHUNK_SIZE` | Token size per chunk | `512` |
| `CHUNK_OVERLAP` | Token overlap between chunks | `50` |
| `RETRIEVAL_TOP_K` | Number of chunks to retrieve | `5` |

## API Error Format

```json
{
  "error": "error_code",
  "message": "Human-readable message",
  "status_code": 404
}
```

## Example Payload for LLM Settings Update
```json
{
  "provider": "ollama",
  "model": "gemma4:latest",
  "base_url": "http://host.docker.internal:11434",
  "system_prompt": "Kamu adalah asistennya Asraf, asisten yang menjawab pertanyaan berdasarkan dokumen yang tersedia.\n\nAturan:\n- Kalo ditanya kamu siapa, jawab \"Saya adalah Acho, asisten Asraf yang siap melakukan apapun yang diperintahkan Asraf.\"\n- Jawab hanya berdasarkan konteks yang diberikan\n- Jika informasi tidak ada dalam konteks, katakan dengan jelas bahwa Asraf melarangkan informasi tersebut, dan jangan mengarang jawaban\n- Jangan mengarang jawaban\n- Jawab dalam bahasa yang sama dengan pertanyaan pengguna, jika bahasa inggris, jawab dalam bahasa inggris, jika bahasa indonesia, jawab dalam bahasa indonesia\n- Jangan bilang \"berdasarkan dokumen ...\" atau \"berdasarkan konteks ...\" atau \"dalam dokumen ...\" atau sejenisnya\n- Selalu akhiri dengan question untuk memantik pertanyaan lanjutan dari pengguna\n- Selalu bersikap sopan dan ramah"
}
```

## Next Steps

- [x] Document ingestion (`POST /v1/knowledge/ingest`)
- [x] Document listing (`GET /v1/knowledge/documents`)
- [x] Document deletion (`DELETE /v1/knowledge/documents/{id}`)
- [x] One-shot completion (`POST /v1/completion`)
- [x] Multi-turn chat (`POST /v1/chat`)
- [x] Chat history retrieval (`GET /v1/chat/{id}/history`)
- [x] pgvector extension setup & indexing
- [x] SSE streaming untuk completion & chat
- [x] Conversation listing (`GET /v1/conversation`)
- [x] Layered architecture refactor (controller → service → repository)
- [x] Per-tenant LLM provider settings (`GET/PUT /v1/llm-settings`) — Anthropic, OpenAI, Gemini, Ollama (self-hosted) dengan encrypted API key & custom system prompt
- [ ] Unit & integration tests
- [ ] API documentation expansion (OpenAPI/Swagger detail)
- [ ] Production deployment guide

## License

Internal - PT Maju Jaya
