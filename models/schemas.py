from datetime import datetime
from uuid import UUID

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
