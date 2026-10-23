from app.core.security import hash_csrf_token, verify_csrf_token
from typing import Optional, List
from fastapi import Depends, HTTPException, status, Request, Cookie
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.auth import AuthService, get_roles_from_token
from app.models import User, UserRole
from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)


async def get_db() -> AsyncSession:
    async for session in get_async_session():
        yield session


async def get_current_user(
    request: Request,
    access_token: Optional[str] = Cookie(None, alias="access_token"),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = access_token
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_service = AuthService(db)
    user = await auth_service.verify_token(token)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


def require_roles(*allowed_roles: UserRole):
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return role_checker


require_viewer = require_roles(UserRole.VIEWER, UserRole.OPERATOR, UserRole.ADMIN)
require_operator = require_roles(UserRole.OPERATOR, UserRole.ADMIN)
require_admin = require_roles(UserRole.ADMIN)


async def verify_csrf(
    request: Request,
    x_csrf_token: Optional[str] = Cookie(None, alias="csrf_token"),
) -> None:
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        csrf_header = request.headers.get("X-CSRF-Token")
        if not csrf_header or not x_csrf_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token missing",
            )
        if not verify_csrf_token(csrf_header, x_csrf_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid CSRF token",
            )


async def get_optional_user(
    request: Request,
    access_token: Optional[str] = Cookie(None, alias="access_token"),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    token = access_token
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if not token:
        return None

    auth_service = AuthService(db)
    user = await auth_service.verify_token(token)
    if user and user.is_active:
        return user
    return None