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
