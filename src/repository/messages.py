from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.database import Messages


async def get_all_by_conversation_repo(conversation_id: UUID, session: AsyncSession) -> list[Messages]:
    result = await session.execute(
        select(Messages)
        .where(Messages.conversation_id == conversation_id)
        .order_by(Messages.created_at.asc())
    )
    return result.scalars().all()


async def create_messages_repo(
    conversation_id: UUID, user_content: str, assistant_content: str, session: AsyncSession
) -> None:
    session.add_all(
        [
            Messages(conversation_id=conversation_id, role="user", content=user_content),
            Messages(conversation_id=conversation_id, role="assistant", content=assistant_content),
        ]
    )
    await session.commit()
