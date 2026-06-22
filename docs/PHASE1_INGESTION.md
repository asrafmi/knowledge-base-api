# Phase 1: Document Ingestion Pipeline

Document upload, parsing, chunking, dan embedding untuk knowledge base.

## Overview

Build the document ingestion pipeline dengan 3 API endpoints:
- `POST /v1/knowledge/ingest` — Upload & process dokumen
- `GET /v1/knowledge/documents` — List dokumen per tenant
- `DELETE /v1/knowledge/documents/{id}` — Hapus dokumen

**Timeline**: ~50 menit (7 steps)

---

## Step 1: Database Migration

**File**: `alembic/versions/002_documents_schema.py`

**Time**: 5 min

Create migration with 2 new tables:

### documents table
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    content_type VARCHAR(50),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### document_chunks table
```sql
-- First, enable pgvector extension (one-time setup)
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    embedding vector(1024),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- HNSW index untuk efficient similarity search (Phase 2)
CREATE INDEX ON document_chunks USING hnsw (embedding vector_cosine_ops);

-- Composite index untuk multi-tenant filter
CREATE INDEX ON document_chunks (company_id, tenant_id);
```

### Migration file structure
```python
"""Add documents and document_chunks tables

Revision ID: 002
Revises: 001
Create Date: 2026-06-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

revision = '002'
down_revision = '001'

def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('content_type', sa.String(50), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), server_default='{}', nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create document_chunks table with pgvector
    op.create_table(
        'document_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chunk_text', sa.Text(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('embedding', Vector(dim=1024), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), server_default='{}', nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create HNSW index for similarity search
    op.execute("CREATE INDEX ON document_chunks USING hnsw (embedding vector_cosine_ops)")
    
    # Create composite index for multi-tenant filter
    op.create_index('idx_document_chunks_company_tenant', 'document_chunks', 
                   ['company_id', 'tenant_id'])

def downgrade() -> None:
    op.drop_table('document_chunks')
    op.drop_table('documents')
```

### Execute
```bash
alembic upgrade head
```

---

## Step 2: ORM Models

**File**: `models/database.py`

**Time**: 5 min

Add 2 new model classes after Tenant:

```python
class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(50), nullable=True)
    metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    embedding = Column(Vector(1024), nullable=True)
    metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="chunks")
```

**Imports needed**:
```python
from sqlalchemy import JSON
from pgvector.sqlalchemy import Vector
```

---

## Step 3: Pydantic Schemas

**File**: `models/schemas.py`

**Time**: 3 min

Add 4 new response schemas at end of file:

```python
class DocumentResponse(BaseModel):
    id: UUID
    company_id: UUID
    tenant_id: UUID
    filename: str
    content_type: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentItemResponse(BaseModel):
    id: UUID
    filename: str
    chunk_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    documents: list[DocumentItemResponse]


class IngestionResponse(BaseModel):
    document_id: UUID
    filename: str
    chunks_created: int
    status: str
```

**Imports needed**:
```python
from typing import Optional
```

---

## Step 4: Ingestion Service

**File**: `services/ingestion.py` (NEW)

**Time**: 10 min

Create new file dengan text parsing & chunking functions:

```python
import tempfile
import tiktoken
from pathlib import Path

from pypdf import PdfReader
from docx import Document as DocxDocument
from fastapi import UploadFile


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks based on token count using tiktoken"""
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


def parse_pdf(file_path: str) -> str:
    """Extract text from PDF file"""
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text


def parse_docx(file_path: str) -> str:
    """Extract text from DOCX file"""
    doc = DocxDocument(file_path)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text


def parse_txt(file_path: str) -> str:
    """Read text from TXT file"""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def parse_file(file_path: str, content_type: str) -> str:
    """Route to correct parser based on content type"""
    if content_type == "application/pdf":
        return parse_pdf(file_path)
    elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return parse_docx(file_path)
    elif content_type == "text/plain":
        return parse_txt(file_path)
    else:
        raise ValueError(f"Unsupported content type: {content_type}")


async def save_upload_file(upload_file: UploadFile) -> str:
    """Save uploaded file to temp location, return file path"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(upload_file.filename).suffix) as tmp_file:
        content = await upload_file.read()
        tmp_file.write(content)
        return tmp_file.name
```

**Imports needed**:
- `import tempfile`
- `import tiktoken`
- `from pathlib import Path`
- `from pypdf import PdfReader`
- `from docx import Document as DocxDocument`
- `from fastapi import UploadFile`

---

## Step 5: Embedding Service

**File**: `services/embedding.py` (NEW)

**Time**: 5 min

Create new file dengan Voyage AI integration:

```python
import voyageai
from core.config import settings


async def embed_chunks(chunks: list[str], input_type: str = "document") -> list[list[float]]:
    """
    Embed chunks using Voyage AI
    Returns list of embeddings (each is list of 1024 floats)
    """
    client = voyageai.Client(api_key=settings.voyage_api_key)
    
    result = client.embed(
        texts=chunks,
        model="voyage-4",
        input_type=input_type
    )
    
    return result.embeddings


async def embed_query(query: str) -> list[float]:
    """
    Embed a single query for retrieval
    Returns single embedding (list of 1024 floats)
    """
    client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)
    
    result = client.embed(
        texts=[query],
        model="voyage-3",
        input_type="query"
    )
    
    return result.embeddings[0]
```

**Imports needed**:
- `import voyageai`
- `from core.config import settings`

---

## Step 6: Knowledge Router

**File**: `api/v1/knowledge.py` (NEW)

**Time**: 20 min

Create new router dengan 3 endpoints:

```python
import os
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_company_id, validate_tenant
from db.session import get_session
from models.database import Document, DocumentChunk
from models.schemas import DocumentListResponse, IngestionResponse
from services.embedding import embed_chunks
from services.ingestion import chunk_text, parse_file, save_upload_file

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}


@router.post("/ingest", response_model=IngestionResponse)
async def ingest_document(
    file: UploadFile = File(...),
    company_id: UUID = Depends(get_company_id),
    tenant_id: UUID = Depends(validate_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Upload and ingest document into knowledge base"""
    
    # Validate file type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "unsupported_file_type",
                "message": f"Supported types: PDF, DOCX, TXT. Got: {file.content_type}",
            },
        )
    
    # Validate filename exists
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail={"error": "empty_filename", "message": "File must have a name"},
        )
    
    # Save uploaded file to temp
    temp_path = None
    try:
        temp_path = await save_upload_file(file)
        
        # Check file size
        file_size = os.path.getsize(temp_path)
        if file_size == 0:
            raise HTTPException(
                status_code=400,
                detail={"error": "empty_file", "message": "Uploaded file is empty"},
            )
        
        # Parse file
        try:
            text = parse_file(temp_path, file.content_type)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "parse_error",
                    "message": f"Failed to parse file: {str(e)}",
                },
            )
        
        # Chunk text
        chunks = chunk_text(text)
        
        if not chunks:
            raise HTTPException(
                status_code=400,
                detail={"error": "no_chunks", "message": "File produced no text chunks"},
            )
        
        # Embed chunks
        try:
            embeddings = await embed_chunks(chunks)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "embedding_error",
                    "message": f"Failed to embed chunks: {str(e)}",
                },
            )
        
        # Save to database
        document = Document(
            company_id=company_id,
            tenant_id=tenant_id,
            filename=file.filename,
            content_type=file.content_type,
            metadata={"file_size": file_size},
        )
        session.add(document)
        await session.flush()  # Get document ID
        
        # Create chunks
        chunk_records = [
            DocumentChunk(
                document_id=document.id,
                company_id=company_id,
                tenant_id=tenant_id,
                chunk_text=chunk,
                chunk_index=i,
                embedding=embeddings[i] if embeddings else None,
                metadata={"chunk_size_tokens": len(chunk.split())},
            )
            for i, chunk in enumerate(chunks)
        ]
        session.add_all(chunk_records)
        
        await session.commit()
        
        return IngestionResponse(
            document_id=document.id,
            filename=file.filename,
            chunks_created=len(chunks),
            status="success",
        )
    
    finally:
        # Cleanup temp file
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    company_id: UUID = Depends(get_company_id),
    tenant_id: UUID = Depends(validate_tenant),
    session: AsyncSession = Depends(get_session),
):
    """List all documents for tenant with chunk counts"""
    
    result = await session.execute(
        select(Document).where(
            (Document.company_id == company_id) & (Document.tenant_id == tenant_id)
        )
    )
    documents = result.scalars().all()
    
    items = []
    for doc in documents:
        chunk_result = await session.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == doc.id)
        )
        chunk_count = len(chunk_result.scalars().all())
        
        items.append(
            DocumentItemResponse(
                id=doc.id,
                filename=doc.filename,
                chunk_count=chunk_count,
                created_at=doc.created_at,
            )
        )
    
    return DocumentListResponse(documents=items)


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: UUID,
    company_id: UUID = Depends(get_company_id),
    tenant_id: UUID = Depends(validate_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Delete document and all its chunks"""
    
    result = await session.execute(
        select(Document).where(
            (Document.id == document_id)
            & (Document.company_id == company_id)
            & (Document.tenant_id == tenant_id)
        )
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "document_not_found",
                "message": "Document not found or does not belong to this tenant",
            },
        )
    
    await session.delete(document)
    await session.commit()
    
    return {"status": "success"}
```

**Imports needed** (all listed at top of file):
```python
import os
from uuid import UUID
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.dependencies import get_company_id, validate_tenant
from db.session import get_session
from models.database import Document, DocumentChunk
from models.schemas import DocumentListResponse, IngestionResponse
from services.embedding import embed_chunks
from services.ingestion import chunk_text, parse_file, save_upload_file
```

---

## Step 7: Register Router

**File**: `api/v1/router.py`

**Time**: 1 min

Add import & include:

```python
from fastapi import APIRouter

from api.v1.companies import router as companies_router
from api.v1.tenants import router as tenants_router
from api.v1.knowledge import router as knowledge_router

router = APIRouter(prefix="/v1")

router.include_router(companies_router)
router.include_router(tenants_router)
router.include_router(knowledge_router)
```

---

## Testing

After all steps are complete, test the endpoints:

### Prepare
```bash
# Get company & tenant IDs (from previous setup)
COMPANY_ID="50fa90d1-6866-4252-8cb2-2bebfc906c78"
TENANT_ID="<your-tenant-id>"
```

### Test 1: Ingest PDF
```bash
curl -X POST http://localhost:8000/v1/knowledge/ingest \
  -H "X-Company-ID: $COMPANY_ID" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -F "file=@sample.pdf"
```

Expected response:
```json
{
  "document_id": "uuid",
  "filename": "sample.pdf",
  "chunks_created": 24,
  "status": "success"
}
```

### Test 2: List Documents
```bash
curl http://localhost:8000/v1/knowledge/documents \
  -H "X-Company-ID: $COMPANY_ID" \
  -H "X-Tenant-ID: $TENANT_ID"
```

Expected response:
```json
[
  {
    "id": "uuid",
    "filename": "sample.pdf",
    "chunk_count": 24,
    "created_at": "2026-06-01T15:00:00"
  }
]
```

### Test 3: Delete Document
```bash
DOCUMENT_ID="<document-id-from-test-2>"

curl -X DELETE http://localhost:8000/v1/knowledge/documents/$DOCUMENT_ID \
  -H "X-Company-ID: $COMPANY_ID" \
  -H "X-Tenant-ID: $TENANT_ID"
```

Expected response:
```json
{
  "status": "success"
}
```

### Test 4: Verify Delete
Re-run Test 2 to confirm document is gone.

---

## Edge Cases Handled

| Case | Status Code | Response |
|------|-------------|----------|
| Unsupported file type | 400 | `unsupported_file_type` |
| Empty file | 400 | `empty_file` |
| No filename | 400 | `empty_filename` |
| Parse error | 500 | `parse_error` |
| Embedding error | 500 | `embedding_error` |
| Document not found (delete) | 404 | `document_not_found` |
| Wrong tenant (delete) | 404 | `document_not_found` |

---

## Important Notes

1. **pgvector enabled** — Embeddings stored as `vector(1024)` type with HNSW indexing.
   - Ready for similarity search in Phase 2 (no schema changes needed)
   - Query: `ORDER BY embedding <=> query_vector LIMIT 5` for cosine similarity
   - HNSW index ensures O(log n) performance even with 1M+ chunks
2. **Async all the way** — All DB operations use AsyncSession.
3. **Multi-tenant isolation** — All queries filtered by company_id + tenant_id.
4. **Transaction safety** — Ingest wraps in transaction (commit all or nothing).
5. **Temp file cleanup** — Uses try/finally to ensure temp files deleted.
6. **Metadata** — Document stores file_size, DocumentChunk stores chunk_size_tokens.

---

## Summary

| Step | Time | What |
|------|------|------|
| 1 | 5 min | Create migration (002_documents_schema.py) & run alembic upgrade |
| 2 | 5 min | Add Document & DocumentChunk models to models/database.py |
| 3 | 3 min | Add 3 schemas to models/schemas.py |
| 4 | 10 min | Create services/ingestion.py (parsing + chunking) |
| 5 | 5 min | Create services/embedding.py (Voyage AI) |
| 6 | 20 min | Create api/v1/knowledge.py (3 endpoints) |
| 7 | 1 min | Register router in api/v1/router.py |
| **Total** | **49 min** | **Full ingestion pipeline ready** |

Then test all 4 test cases to verify everything works.
