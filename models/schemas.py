from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel


class CompanyCreate(BaseModel):
    name: str


class CompanyUpdate(BaseModel):
    name: str


class CompanyResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


class TenantCreate(BaseModel):
    name: str


class TenantUpdate(BaseModel):
    name: str


class TenantResponse(BaseModel):
    id: UUID
    company_id: UUID
    name: str
    created_at: datetime

    class Config:
        from_attributes = True

class DocumentResponse(BaseModel):
    id: UUID
    company_id: UUID
    tenant_id: UUID
    filename: str
    content_type: Optional[str] = None
    meta: dict | None
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
