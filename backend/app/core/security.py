from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
_INSECURE_DEVELOPMENT_JWT_KEY = "dev_jwt_secret_change_in_production_min_32_bytes_long"
_ALLOWED_JWT_ALGORITHMS = {"HS256", "HS384", "HS512"}


def jwt_signing_is_configured() -> bool:
    key = settings.jwt_secret_key.encode("utf-8")
    return (
        len(key) >= 32
        and len(set(key)) >= 16
        and settings.jwt_secret_key != _INSECURE_DEVELOPMENT_JWT_KEY
        and settings.jwt_algorithm in _ALLOWED_JWT_ALGORITHMS
    )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str | Any, expires_delta: Optional[timedelta] = None) -> str:
    if not jwt_signing_is_configured():
        raise RuntimeError(
            "JWT authentication requires a supported signing key of at least 32 bytes with sufficient key diversity"
        )
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode = {"exp": expire, "sub": str(subject)}
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token_subject(token: str) -> str | None:
    if not jwt_signing_is_configured():
        return None
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
    subject = payload.get("sub")
    expiration = payload.get("exp")
    if not isinstance(subject, str) or not subject or not isinstance(expiration, (int, float)):
        return None
    return subject
