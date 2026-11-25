from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from egm_common.auth import create_access_token
from ..config import settings
from ..db import get_session
from ..models import User
from ..schemas import Token, UserLogin
from ..service import authenticate_user, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=Token)
async def login(
    payload: UserLogin, session: AsyncSession = Depends(get_session)
) -> Token:
    user = await authenticate_user(session, payload.username, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
        )
    access_token = create_access_token({"sub": user.username})
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)) -> dict:
    return {
        "id": str(current_user.id),
        "username": current_user.username,
        "role": current_user.role,
        "is_active": current_user.is_active,
    }
