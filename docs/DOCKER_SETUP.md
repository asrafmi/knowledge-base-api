# Docker Setup Guide

Complete Docker-based setup untuk Knowledge Base API dengan automatic database initialization.

## Architecture

```
docker-compose.yml
├── postgres (PostgreSQL 16)
│   └── Database instance
├── migrator (Migration Runner)
│   ├── Waits for postgres healthy
│   ├── Installs pgvector extension
│   ├── Runs alembic migrations
│   └── Exits after completion
└── app (FastAPI Application)
    ├── Waits for migrator completion
    └── Runs on port 8000
```

## Prerequisites

- Docker
- Docker Compose
- `.env` file dengan API keys (copy dari `.env.example`)

## Quick Start

### 1. Build & Start Everything

```bash
cd misc/docker
docker-compose up --build
```

**Output should show:**
```
knowledge-base-postgres  | ... listening on IPv4 address "0.0.0.0", port 5432
knowledge-base-db-init   | ✓ PostgreSQL is ready
knowledge-base-db-init   | ✓ pgvector extension ready
knowledge-base-db-init   | ✓ Running database migrations...
knowledge-base-db-init   | ✓ Database initialization complete!
knowledge-base-app       | INFO:     Uvicorn running on http://0.0.0.0:8000
```

Server ready di: `http://localhost:8000`
API Docs: `http://localhost:8000/docs`

### 2. Test API

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

### 3. Stop Containers

```bash
docker-compose down
```

---

## Container Details

### postgres

**Image:** `postgres:16-alpine`

**What it does:**
- Provides PostgreSQL database instance
- Health check: `pg_isready`
- Volume: `postgres_data` (persistent)

**Ports:** `5432` (accessible from host)

**Environment:**
```
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=knowledge_base
```

---

### migrator

**Image:** Custom (built from `Dockerfile`)

**What it does:**
1. Waits for PostgreSQL to be healthy
2. Creates pgvector extension
3. Runs alembic migrations (001 + 002)
4. Exits with success/failure

**Command:**
```bash
psql -h postgres -U postgres -d knowledge_base -c "CREATE EXTENSION IF NOT EXISTS vector" &&
alembic upgrade head
```

**Depends on:** `postgres` (health check)

**Environment:**
```
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/knowledge_base
```

**Restart policy:** `on-failure` (retries if migration fails)

---

### app

**Image:** Custom (built from `Dockerfile`)

**Build stages:**
1. **base** — Python 3.11 + system dependencies
2. **builder** — Install Python dependencies (pip wheels)
3. **final** — Copy builder artifacts, ready to run

**What it does:**
- Starts FastAPI server (uvicorn)
- Only runs after migrator completes successfully

**Command:**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Depends on:** `migrator` (service_completed_successfully)

**Volumes:**
```
/app  → Entire project (for hot reload in dev)
```

**Environment:**
```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/knowledge_base
ANTHROPIC_API_KEY=<from .env>
VOYAGE_API_KEY=<from .env>
```

**Ports:** `8000` (FastAPI server)

---

## Workflows

### Development Workflow

```bash
# Start everything
docker-compose up --build

# In another terminal, make code changes
# Changes auto-reload in running app container

# Stop when done
docker-compose down
```

### Rebuild After Schema Changes

If you modify `models/database.py` or create new migrations:

```bash
# Rebuild image
docker-compose build --no-cache

# Run migrator to apply new migrations
docker-compose run migrator

# Restart app
docker-compose restart app
```

Or simpler:
```bash
docker-compose up --build
```

### View Logs

```bash
# All containers
docker-compose logs -f

# Specific container
docker-compose logs -f db-init
docker-compose logs -f app
```

### Access PostgreSQL Directly

```bash
# Connect to postgres container
docker exec -it knowledge-base-postgres psql -U postgres -d knowledge_base

# Inside psql:
knowledge_base=# \dt          # List tables
knowledge_base=# SELECT * FROM documents;
knowledge_base=# \q           # Quit
```

---

## Troubleshooting

### Error: "Could not open extension control file"
**Cause:** pgvector not installed in PostgreSQL image
**Solution:** This should be handled by `db-init` container. If error persists:
```bash
docker exec -it knowledge-base-postgres apt-get install -y postgresql-16-pgvector
```

### Error: "service_completed_successfully" not found
**Cause:** Older Docker Compose version
**Solution:** Update Docker Compose to latest version

### Port 5432 already in use
**Solution:** Stop other PostgreSQL instances or change port in docker-compose:
```yaml
ports:
  - "5433:5432"  # Change to different host port
```

### App can't connect to database
**Solution:** Check `db-init` logs:
```bash
docker-compose logs db-init
```

---

## File Structure

```
misc/docker/
├── docker-compose.yml     # Orchestration (3 services)
├── Dockerfile             # Multi-stage build image
└── README.md             # This file

Project root/
├── alembic/              # Migrations
├── .env                  # Environment variables
├── requirements.txt      # Python dependencies
└── main.py              # FastAPI entry point
```

---

## Environment Variables

All variables must be in `.env` file (copy from `.env.example`):

```env
# Database Configuration
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=knowledge_base
DB_PORT=5432

# Application Configuration
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/knowledge_base
APP_PORT=8000

# API Keys (required)
ANTHROPIC_API_KEY=sk-ant-...
VOYAGE_API_KEY=pa-...

# RAG Parameters (optional, have defaults)
CHUNK_SIZE=512
CHUNK_OVERLAP=50
RETRIEVAL_TOP_K=5
```

**Note:** docker-compose reads all variables from `.env` file automatically

---

## Performance Tips

1. **Skip rebuilds for code changes:**
   ```bash
   docker-compose up  # Don't use --build if only code changed
   ```

2. **Use `.dockerignore` to speed up builds:**
   Already handled in project

3. **Persistent database:**
   - Data saved in `postgres_data` volume
   - Survives `docker-compose down` (use `docker-compose down -v` to delete)

---

## Next Steps

- Read [PHASE1_INGESTION.md](PHASE1_INGESTION.md) untuk implement document ingestion
- Check [README.md](../README.md) untuk API documentation
- View [CLAUDE.md](../CLAUDE.md) untuk build specification
