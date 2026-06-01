from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from models.database import Company
from models.schemas import CompanyCreate, CompanyResponse, CompanyUpdate

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("", response_model=CompanyResponse)
async def create_company(
    company: CompanyCreate,
    session: AsyncSession = Depends(get_session),
):
    db_company = Company(name=company.name)
    session.add(db_company)
    await session.commit()
    await session.refresh(db_company)
    return db_company


@router.get("", response_model=list[CompanyResponse])
async def list_companies(
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Company))
    companies = result.scalars().all()
    return companies


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(
            status_code=404,
            detail={"error": "company_not_found", "message": "Company tidak ditemukan"},
        )
    return company


@router.patch("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: UUID,
    company: CompanyUpdate,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Company).where(Company.id == company_id))
    db_company = result.scalar_one_or_none()
    if not db_company:
        raise HTTPException(
            status_code=404,
            detail={"error": "company_not_found", "message": "Company tidak ditemukan"},
        )
    db_company.name = company.name
    await session.commit()
    await session.refresh(db_company)
    return db_company


@router.delete("/{company_id}")
async def delete_company(
    company_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Company).where(Company.id == company_id))
    db_company = result.scalar_one_or_none()
    if not db_company:
        raise HTTPException(
            status_code=404,
            detail={"error": "company_not_found", "message": "Company tidak ditemukan"},
        )
    await session.delete(db_company)
    await session.commit()
    return {"status": "success"}
