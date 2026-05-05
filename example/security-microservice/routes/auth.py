"""POST /v1/auth/login — exchange username+password for a JWT.

Returns ONLY {access_token, token_type, expires_in}. No user object.
Returning the user here is a frequent leak path — clients stash it in
localStorage and you've handed every XSS attacker a free identity."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from auth import authenticate, mint_jwt
from config import Settings, get_settings
from models import LoginRequest, LoginResponse


router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse,
              responses={401: {"description": "wrong credentials"}})
async def login(
    payload: LoginRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> LoginResponse:
    if not authenticate(payload.username, payload.password,
                          secret=settings.jwt_secret):
        # Same error shape regardless of which field was wrong.
        # Even the *timing* matches because authenticate() always
        # hashes a password. See auth.py for the rationale.
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={"code": "auth.bad_credentials",
                     "message": "invalid username or password"},
        )
    token, expires_in = mint_jwt(sub=payload.username.lower(),
                                   settings=settings)
    return LoginResponse(access_token=token, expires_in=expires_in)
