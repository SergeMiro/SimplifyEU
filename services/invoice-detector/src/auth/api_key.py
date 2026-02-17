"""
API Key Authentication — copied from subscription-analyzer pattern.
"""
import logging
from typing import Optional

from fastapi import Security, Header, HTTPException, status
from fastapi.security.api_key import APIKeyHeader

from ..config import settings

logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


async def get_current_account(
    api_key: str = Security(api_key_header),
    account_id: str = Header(..., alias="X-Account-ID"),
) -> str:
    """
    Validate API key and return the account ID.
    In development, accepts sk_test_* keys.
    In production, validates against Supabase.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )

    if not account_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing account ID",
        )

    # Development mode: accept test keys
    if not settings.is_production and api_key.startswith("sk_test_"):
        logger.debug(f"Dev mode: accepted test key for account {account_id}")
        return account_id

    # Production mode: reject test keys
    if settings.is_production and api_key.startswith("sk_test_"):
        logger.warning(f"BLOCKED: test key used in production for account {account_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Test keys are not allowed in production",
        )

    # Validate against Supabase
    try:
        from passlib.hash import bcrypt
        from ..db.client import supabase

        result = (
            supabase.table("api_keys")
            .select("key_hash, is_active")
            .eq("account_id", account_id)
            .eq("is_active", True)
            .execute()
        )

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )

        for key_record in result.data:
            stored_hash = key_record["key_hash"]
            if bcrypt.verify(api_key, stored_hash):
                return account_id

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auth validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error",
        )
