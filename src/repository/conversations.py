from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.database import Conversations


async def get_by_id_repo(
    conversation_id: UUID, company_id: UUID, tenant_id: UUID, session: AsyncSession
) -> Conversations | None:
    result = await session.execute(
        select(Conversations).where(
            (Conversations.id == conversation_id)
            & (Conversations.company_id == company_id)
            & (Conversations.tenant_id == tenant_id)
        )
    )
    return result.scalar_one_or_none()


async def get_all_by_tenant_repo(
    company_id: UUID, tenant_id: UUID, session: AsyncSession
) -> list[Conversations]:
    result = await session.execute(
        select(Conversations).where(
            (Conversations.company_id == company_id) & (Conversations.tenant_id == tenant_id)
        )
    )
    return result.scalars().all()


async def create_conversation_repo(
    company_id: UUID, tenant_id: UUID, user_id: str | None, session: AsyncSession
) -> Conversations:
    conversation = Conversations(
        company_id=company_id,
        tenant_id=tenant_id,
        user_id=user_id,
    )
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)

    return conversation
