from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_session
from src.models.schemas import CompanyCreate, CompanyResponse, CompanyUpdate
from src.services.companies import (
    create_company_service,
    delete_company_service,
    get_all_companies_service,
    get_company_service,
    update_company_service,
)

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("", response_model=CompanyResponse)
async def create_company(
    company: CompanyCreate,
    session: AsyncSession = Depends(get_session),
):
    company = await create_company_service(session, company.name)

    return company


@router.get("", response_model=list[CompanyResponse])
async def list_companies(
    session: AsyncSession = Depends(get_session),
):
    companies = await get_all_companies_service(session)

    return companies


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    company = await get_company_service(company_id, session)

    return company


@router.patch("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: UUID,
    company: CompanyUpdate,
    session: AsyncSession = Depends(get_session),
):
    updated_company = await update_company_service(company_id, company.name, session)

    return updated_company


@router.delete("/{company_id}")
async def delete_company(
    company_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    await delete_company_service(company_id, session)

    return {"status": "success"}
