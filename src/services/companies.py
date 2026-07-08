from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.database import Company
from src.repository.companies import (
    create_company_repo,
    delete_company_repo,
    get_all_companies_repo,
    get_by_id_repo,
    update_company_repo,
)


async def get_all_companies_service(session: AsyncSession) -> list[Company]:
    companies = await get_all_companies_repo(session)

    return companies


async def create_company_service(session: AsyncSession, name: str) -> Company:
    company = await create_company_repo(session, name)

    return company


async def get_company_service(company_id: UUID, session: AsyncSession) -> Company:
    company = await get_by_id_repo(company_id, session)
    if not company:
        raise HTTPException(
            status_code=404,
            detail={"error": "company_not_found", "message": "Company tidak ditemukan"},
        )

    return company


async def update_company_service(company_id: UUID, name: str, session: AsyncSession) -> Company:
    company = await get_company_service(company_id, session)
    company = await update_company_repo(company, name, session)

    return company


async def delete_company_service(company_id: UUID, session: AsyncSession) -> None:
    company = await get_company_service(company_id, session)
    await delete_company_repo(company, session)