import os
from uuid import UUID

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.voyage.index import embed_chunks
from src.models.schemas import DocumentItemResponse, DocumentListResponse, IngestionResponse
from src.repository.document_chunks import count_by_document_repo, create_chunks_repo
from src.repository.documents import (
    create_document_repo,
    delete_document_repo,
    get_all_by_tenant_repo,
    get_by_id_repo,
)
from src.services.ingestion import chunk_text, parse_file, save_upload_file

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}


async def ingest_document_service(
    file: UploadFile, company_id: UUID, tenant_id: UUID, session: AsyncSession
) -> IngestionResponse:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "unsupported_file_type",
                "message": f"Supported types: PDF, DOCX, TXT. Got: {file.content_type}",
            },
        )

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail={"error": "empty_filename", "message": "File must have a name"},
        )

    temp_path = None
    try:
        temp_path = await save_upload_file(file)

        file_size = os.path.getsize(temp_path)
        if file_size == 0:
            raise HTTPException(
                status_code=400,
                detail={"error": "empty_file", "message": "Uploaded file is empty"},
            )

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

        chunks = chunk_text(text)

        if not chunks:
            raise HTTPException(
                status_code=400,
                detail={"error": "no_chunks", "message": "File produced no text chunks"},
            )

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

        document = await create_document_repo(
            company_id=company_id,
            tenant_id=tenant_id,
            filename=file.filename,
            content_type=file.content_type,
            meta={"file_size": file_size},
            session=session,
        )

        await create_chunks_repo(
            document_id=document.id,
            company_id=company_id,
            tenant_id=tenant_id,
            chunks=chunks,
            embeddings=embeddings,
            session=session,
        )

        await session.commit()

        return IngestionResponse(
            document_id=document.id,
            filename=file.filename,
            chunks_created=len(chunks),
            status="success",
        )

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


async def list_documents_service(
    company_id: UUID, tenant_id: UUID, session: AsyncSession
) -> DocumentListResponse:
    documents = await get_all_by_tenant_repo(company_id, tenant_id, session)

    items = [
        DocumentItemResponse(
            id=doc.id,
            filename=doc.filename,
            chunk_count=await count_by_document_repo(doc.id, session),
            created_at=doc.created_at,
        )
        for doc in documents
    ]

    return DocumentListResponse(documents=items)


async def delete_document_service(
    document_id: UUID, company_id: UUID, tenant_id: UUID, session: AsyncSession
) -> None:
    document = await get_by_id_repo(document_id, company_id, tenant_id, session)

    if not document:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "document_not_found",
                "message": "Documents not found or does not belong to this tenant",
            },
        )

    await delete_document_repo(document, session)
