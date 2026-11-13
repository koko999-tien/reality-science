from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.modules.iam_governance.schemas import UserCreate, UserResponse
from app.modules.iam_governance.service import create_user_with_actor

router = APIRouter(prefix="/iam", tags=["iam"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    user = await create_user_with_actor(db, payload)
    return UserResponse(id=user.id, email=user.email, display_name=payload.display_name)
