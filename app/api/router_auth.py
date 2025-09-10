from typing import Optional
from fastapi import Header, HTTPException, status
from ..core.config import settings
from ..services.cognito_jwt_verifier import CognitoJWTVerifier
import logging

log = logging.getLogger(__name__)

async def get_current_sub(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    x_debug_sub: Optional[str] = Header(default=None, alias="X-Debug-Sub"),
) -> str:
    if settings.allow_debug_sub and x_debug_sub:
        return x_debug_sub

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    token = authorization.split(" ", 1)[1].strip()
    try:
        return CognitoJWTVerifier.sub_from_token(token)
    except Exception as e:
        log.warning("JWT verify failed: %s", e)  # <- this will say EXACT reason
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
