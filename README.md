# Knowledge Base API

REST API untuk knowledge base dengan RAG pipeline dan multi-turn chat. Dibangun dengan FastAPI + PostgreSQL (pgvector) + Claude (Anthropic) + Voyage AI untuk embedding.

## Quick Start

### Prerequisites
- Docker & Docker Compose
- (Optional) Python 3.11+ untuk local development

### Setup dengan Docker (Recommended)

1. **Setup Environment Variables**
```bash
cp .env.example .env
# Edit .env dengan API keys (ANTHROPIC_API_KEY, VOYAGE_API_KEY)
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

### Chat — Multi-Turn Conversation
- `POST /v1/chat` — Create conversation
  - **Headers:** `X-Company-ID`, `X-Tenant-ID`
  - **Body:** `{"user_id": "..."}` (optional)
  - **Response:** conversation_id
- `POST /v1/chat/{conversation_id}/message` — Send message
  - **Headers:** `X-Company-ID`, `X-Tenant-ID`
  - **Body:** `{"message": "..."}`
  - **Response:** answer + source chunks
- `GET /v1/chat/{conversation_id}/history` — Get conversation history
  - **Headers:** `X-Company-ID`, `X-Tenant-ID`
  - **Response:** list of all messages (user + assistant)

**Multi-tenant Headers (Required for knowledge base endpoints):**
```
X-Company-ID: <uuid>
X-Tenant-ID: <uuid>
```

## Project Structure

```
knowledge-base-api/
├── main.py                 # FastAPI app entry point
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (gitignored)
├── .env.example           # Environment template
├── alembic/               # Database migrations
│   ├── env.py             # Alembic configuration
│   ├── versions/          # Migration files
│   └── script.py.mako     # Migration template
├── core/
│   ├── config.py          # Settings & environment variables
│   └── dependencies.py    # FastAPI dependencies & validation
├── db/
│   └── session.py         # AsyncSession & engine setup
├── models/
│   ├── database.py        # SQLAlchemy ORM models
│   └── schemas.py         # Pydantic request/response schemas
├── api/
│   └── v1/
│       ├── router.py      # Main API router
│       ├── companies.py   # Company endpoints
│       └── tenants.py     # Tenant endpoints
├── services/
│   ├── ingestion.py       # Document parsing & chunking
│   ├── retrieval.py       # Vector similarity search (pgvector)
│   └── llm.py             # Claude integration & RAG context
├── infrastructure/
│   └── voyage/
│       └── index.py       # Voyage AI embedding client
└── misc/docker/
    └── docker-compose.yml # PostgreSQL container
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

## Multi-Tenant Convention

Semua request yang berhubungan dengan knowledge base **wajib membawa header**:

```
X-Company-ID: <uuid>   # Company yang mengakses
X-Tenant-ID: <uuid>    # Tenant dalam company tersebut (untuk validation)
```

Validasi dilakukan di `core/dependencies.py`:
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
| `ANTHROPIC_API_KEY` | Claude API key | `sk-ant-...` |
| `VOYAGE_API_KEY` | Voyage AI API key | `pa-...` |
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

## Next Steps

- [ ] Document ingestion (`POST /v1/knowledge/ingest`)
- [ ] Document listing (`GET /v1/knowledge/documents`)
- [ ] Document deletion (`DELETE /v1/knowledge/documents/{id}`)
- [ ] One-shot completion (`POST /v1/completion`)
- [ ] Multi-turn chat (`POST /v1/chat`)
- [ ] Chat history retrieval (`GET /v1/chat/{id}/history`)
- [ ] pgvector extension setup & indexing
- [ ] Unit & integration tests
- [ ] API documentation
- [ ] Production deployment guide

## License

Internal - PT Maju Jaya
