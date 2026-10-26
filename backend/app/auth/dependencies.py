"""Vulture Bot - Authentication dependencies and permission checks."""

from __future__ import annotations

from typing import Optional, Annotated
from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.database.session import get_db
from app.database.models.user import User
from app.security.auth import decode_session_token


async def get_current_user_optional(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Optional[User]:
    """Retrieve the current logged-in user if a valid session exists."""
    settings = get_settings()
    cookie_token = request.cookies.get(settings.session_cookie_name)

    # Also support Authorization: Bearer <token>
    auth_header = request.headers.get("Authorization")
    token = None
    if cookie_token:
        token = cookie_token
    elif auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]

    if not token:
        return None

    payload = decode_session_token(token)
    if not payload or "sub" not in payload:
        return None

    user_id = payload["sub"]
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user and not user.is_active:
        return None

    return user


async def get_current_user(
    user: Annotated[Optional[User], Depends(get_current_user_optional)],
) -> User:
    """Require an authenticated user."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_admin(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Require an authenticated administrator."""
    settings = get_settings()
    is_admin = user.is_admin or user.is_superadmin or (user.email.lower() in settings.admin_emails_list)
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required for this action.",
        )
    return user
