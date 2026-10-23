from datetime import datetime, timedelta, UTC
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from passlib.context import CryptContext
from secrets import token_urlsafe
import hashlib

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: Dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def generate_csrf_token() -> str:
    return token_urlsafe(32)


def hash_csrf_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def verify_csrf_token(token: str, hashed: str) -> bool:
    return hash_csrf_token(token) == hashed


def generate_pkce_pair() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge (S256)."""
    verifier = token_urlsafe(64)
    challenge = hashlib.sha256(verifier.encode()).digest()
    import base64
    challenge_b64 = base64.urlsafe_b64encode(challenge).decode().rstrip("=")
    return verifier, challenge_b64


def generate_state() -> str:
    return token_urlsafe(32)