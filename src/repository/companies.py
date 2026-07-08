from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.database import Company


async def get_all_companies_repo(session: AsyncSession) -> list[Company]:
    result = await session.execute(select(Company))
    companies = result.scalars().all()

    return companies


async def get_by_id_repo(company_id: UUID, session: AsyncSession) -> Company | None:
    result = await session.execute(select(Company).where(Company.id == company_id))
    return result.scalar_one_or_none()


async def update_company_repo(company: Company, name: str, session: AsyncSession) -> Company:
    company.name = name

    await session.commit()
    await session.refresh(company)

    return company


async def delete_company_repo(company: Company, session: AsyncSession) -> None:
    await session.delete(company)
    await session.commit()

async def create_company_repo(session: AsyncSession, name: str) -> Company:
    company = Company(name=name)
    session.add(company)

    await session.commit()
    await session.refresh(company)

    return company