from __future__ import annotations

import base64
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from jose import JWTError, jwt

# Java (jjwt) base64-decodes the secret before use as the HMAC key.
# We must do the same so both services sign/verify with identical key bytes.
_raw_secret = os.getenv("JWT_SECRET", "changeme")
try:
    JWT_SECRET = base64.b64decode(_raw_secret)
except Exception:
    JWT_SECRET = _raw_secret.encode()
JWT_ALGORITHM = "HS256"

jwt_router = APIRouter()


def verify_jwt_or_service_key(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
) -> dict:
    """
    FastAPI dependency for endpoints used by both portals (JWT) and internal
    services like the Nemo LMS (X-Api-Key). Service-key callers get a synthetic
    claims dict with the SERVICE role (full read access, no customer scoping).
    """
    from auth.service_keys import is_valid_service_key

    if x_api_key is not None:
        if is_valid_service_key(x_api_key):
            return {"sub": "service", "roles": ["SERVICE"]}
        raise HTTPException(status_code=401, detail="Invalid API key")
    if authorization is None:
        raise HTTPException(status_code=401, detail="Missing credentials")
    return verify_jwt(authorization)


def verify_jwt(authorization: str = Header(...)) -> dict:
    """FastAPI dependency: extracts and validates the Bearer JWT."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization[7:]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")


def create_token(subject: str, roles: list, expires_minutes: int = 1440) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    return jwt.encode(
        {"sub": subject, "roles": roles, "exp": exp},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


@jwt_router.get("/verify")
async def verify_token_endpoint(claims: dict = __import__("fastapi").Depends(verify_jwt)):
    """Health-check endpoint to verify a token is valid."""
    return {"valid": True, "claims": claims}
