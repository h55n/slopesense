"""API Key generation and management."""

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
    # Check if email already has an active key
    existing = await db.execute(select(ApiKey).where(ApiKey.email == req.email, ApiKey.is_active == True))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="An active API key already exists for this email.")

    # Create new key
    new_key = generate_secure_key()
    api_key_record = ApiKey(
        id=uuid.uuid4(),
        key=new_key,
        name=req.name,
        email=req.email,
        organization=req.organization,
        tier="public",
        is_active=True,
    )
    db.add(api_key_record)
    await db.commit()

    return ApiKeyResponse(
        key=new_key,
        message="Please copy this key and store it safely. It will not be shown again."
    )
