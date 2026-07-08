from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_company_id, validate_tenant
from src.db.session import get_session
from src.models.schemas import DocumentListResponse, IngestionResponse
from src.services.knowledge import (
    delete_document_service,
    ingest_document_service,
    list_documents_service,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("/ingest", response_model=IngestionResponse)
async def ingest_document(
    file: UploadFile = File(...),
    company_id: UUID = Depends(get_company_id),
    tenant_id: UUID = Depends(validate_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Upload and ingest document into knowledge base"""
    return await ingest_document_service(file, company_id, tenant_id, session)


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    company_id: UUID = Depends(get_company_id),
    tenant_id: UUID = Depends(validate_tenant),
    session: AsyncSession = Depends(get_session),
):
    """List all documents for tenant with chunk counts"""
    return await list_documents_service(company_id, tenant_id, session)


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: UUID,
    company_id: UUID = Depends(get_company_id),
    tenant_id: UUID = Depends(validate_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Delete document and all its chunks"""
    await delete_document_service(document_id, company_id, tenant_id, session)

    return {"status": "success"}
