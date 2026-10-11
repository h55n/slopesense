"""API Key generation and management."""

import hashlib
import secrets
import string
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.database import get_db
from backend.models import ApiKey

router = APIRouter(prefix="/v1/apikeys", tags=["apikeys"])


class ApiKeyRequest(BaseModel):
    name: str
    email: EmailStr
    organization: Optional[str] = None


def key_digest(key: str) -> str:
    """Only irreversible digests are stored; a key is shown once."""
    return hashlib.sha256(key.encode()).hexdigest()


class ApiKeyResponse(BaseModel):
    key: str
    message: str


def generate_secure_key() -> str:
    """Generate a secure, random API key."""
    alphabet = string.ascii_letters + string.digits
    return "ss_" + "".join(secrets.choice(alphabet) for _ in range(40))


@router.post("/generate", response_model=ApiKeyResponse)
async def generate_api_key(req: ApiKeyRequest, db: AsyncSession = Depends(get_db)):
    """
    Generate a new SlopeSense API Key.
    """
    if db is None:
        raise HTTPException(status_code=503, detail="API key registry unavailable")
    # Check if email already has an active key
    try:
        existing = await db.execute(
            select(ApiKey).where(ApiKey.email == req.email, ApiKey.is_active.is_(True))
        )
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=503, detail="API key registry unavailable"
        ) from exc
    if existing.scalars().first():
        raise HTTPException(
            status_code=400, detail="An active API key already exists for this email."
        )

    # Create new key
    new_key = generate_secure_key()
    api_key_record = ApiKey(
        id=uuid.uuid4(),
        key=key_digest(new_key),
        name=req.name,
        email=req.email,
        organization=req.organization,
        tier="public",
        is_active=True,
    )
    db.add(api_key_record)
    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=503, detail="API key was not saved") from exc

    return ApiKeyResponse(
        key=new_key,
        message="Please copy this key and store it safely. It will not be shown again.",
    )
