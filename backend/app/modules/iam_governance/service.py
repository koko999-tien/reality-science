from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.iam_governance.models import UserAccount, ResearchActor
from app.modules.iam_governance.schemas import UserCreate
from app.core.security import get_password_hash


async def create_user_with_actor(db: AsyncSession, payload: UserCreate) -> UserAccount:
    user = UserAccount(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
    )
    db.add(user)
    await db.flush()

    actor = ResearchActor(
        user_account_id=user.id,
        display_name=payload.display_name,
    )
    db.add(actor)
    await db.commit()
    await db.refresh(user)
    return user
