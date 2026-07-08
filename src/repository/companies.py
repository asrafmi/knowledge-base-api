from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.database import Company


async def get_all_companies_repo(session: AsyncSession) -> list[Company]:
    result = await session.execute(select(Company))
    companies = result.scalars().all()

    return companies
