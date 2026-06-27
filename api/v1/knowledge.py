import os
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_company_id, validate_tenant
from db.session import get_session
from models.database import Documents, DocumentChunks
from models.schemas import DocumentListResponse, IngestionResponse, DocumentItemResponse
from infrastructure.voyage.index import embed_chunks
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
            embeddings = embed_chunks(chunks)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "embedding_error",
                    "message": f"Failed to embed chunks: {str(e)}",
                },
            )
        
        # Save to database
        document = Documents(
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
            DocumentChunks(
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
        select(Documents).where(
            (Documents.company_id == company_id) & (Documents.tenant_id == tenant_id)
        )
    )
    documents = result.scalars().all()
    
    items = []
    for doc in documents:
        chunk_result = await session.execute(
            select(DocumentChunks).where(DocumentChunks.document_id == doc.id)
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
        select(Documents).where(
            (Documents.id == document_id)
            & (Documents.company_id == company_id)
            & (Documents.tenant_id == tenant_id)
        )
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "document_not_found",
                "message": "Documents not found or does not belong to this tenant",
            },
        )
    
    await session.delete(document)
    await session.commit()
    
    return {"status": "success"}