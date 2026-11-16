from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core.security import create_access_token, jwt_signing_is_configured, verify_password
from app.modules.iam_governance.models import UserAccount
from app.modules.iam_governance.schemas import AccessTokenResponse, LoginRequest, UserCreate, UserResponse
from app.modules.iam_governance.service import create_user_with_actor

router = APIRouter(prefix="/iam", tags=["iam"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    user = await create_user_with_actor(db, payload)
    return UserResponse(id=user.id, email=user.email, display_name=payload.display_name)


@router.post("/login", response_model=AccessTokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> AccessTokenResponse:
    result = await db.execute(select(UserAccount).where(UserAccount.email == str(payload.email)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not jwt_signing_is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is unavailable because token signing is not configured.",
        )
    return AccessTokenResponse(access_token=create_access_token(user.id))
