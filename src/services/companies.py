from sqlalchemy.ext.asyncio import AsyncSession

from src.models.database import Company
from src.repository.companies import get_all_companies_repo

async def get_all_companies_service(session: AsyncSession) -> list[Company]:
    companies = await get_all_companies_repo(session)

    return companies