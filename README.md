# Knowledge Base API

REST API untuk knowledge base dengan RAG pipeline dan multi-turn chat. Dibangun dengan FastAPI + PostgreSQL (pgvector) + Claude (Anthropic) + Voyage AI untuk embedding.

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 16+ dengan pgvector extension
- Docker & Docker Compose (untuk database)

### Setup

1. **Clone & Install Dependencies**
```bash
cd knowledge-base-api
uv venv
source .venv/bin/activate  # atau .venv\Scripts\activate di Windows
pip install -r requirements.txt
```

2. **Setup Environment Variables**
```bash
cp .env.example .env
# Edit .env dengan API keys dan database URL
```

3. **Start PostgreSQL**
```bash
cd misc/docker
docker-compose up -d
```

4. **Run Migrations**
```bash
alembic upgrade head
```

5. **Start Server**
```bash
uvicorn main:app --reload --port 8000
```

Server running di `http://localhost:8000`. API docs tersedia di `http://localhost:8000/docs`

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

**Multi-tenant Headers (Required for tenant endpoints):**
```
X-Company-ID: <uuid>
X-Tenant-ID: <uuid>  # (opsional untuk most endpoints, required untuk context validation)
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
├── services/              # (future)
│   ├── embedding.py       # Voyage AI integration
│   ├── retrieval.py       # Vector search
│   ├── llm.py             # Claude integration
│   └── ingestion.py       # Document parsing & chunking
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

### documents (TODO)
```sql
id UUID PRIMARY KEY
company_id UUID NOT NULL REFERENCES companies(id)
tenant_id UUID NOT NULL REFERENCES tenants(id)
filename TEXT NOT NULL
content_type TEXT
metadata JSONB
created_at TIMESTAMPTZ
```

### document_chunks (TODO)
```sql
id UUID PRIMARY KEY
document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE
company_id UUID NOT NULL
tenant_id UUID NOT NULL
chunk_text TEXT NOT NULL
chunk_index INT NOT NULL
embedding vector(1024)
metadata JSONB
```

### conversations (TODO)
```sql
id UUID PRIMARY KEY
company_id UUID NOT NULL
tenant_id UUID NOT NULL
user_id TEXT
created_at TIMESTAMPTZ
```

### messages (TODO)
```sql
id UUID PRIMARY KEY
conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE
role TEXT NOT NULL CHECK (role IN ('user', 'assistant'))
content TEXT NOT NULL
created_at TIMESTAMPTZ
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
