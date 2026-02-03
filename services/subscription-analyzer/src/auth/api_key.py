import os
import logging
from fastapi import Security, HTTPException, status, Header
from fastapi.security.api_key import APIKeyHeader
from passlib.context import CryptContext
from ..db.client import supabase

logger = logging.getLogger(__name__)

# Environment configuration - SECURITY: Test keys only allowed in development
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_account(
    api_key: str = Security(api_key_header),
    account_id: str = Header(..., alias="X-Account-ID")
) -> str:
    """
    Validates API Key and returns account_id.
    Verifies the hash of the api_key against the stored hash in the database.
    
    SECURITY NOTES:
    - Test/demo keys are ONLY allowed in non-production environments
    - API keys are NEVER logged (even partially)
    - Database errors return generic messages to prevent information disclosure
    """
    # SECURITY: Never log API keys, even partially
    logger.debug(f"[AUTH] Request from account: {account_id}")
    
    # Validate required headers first
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key",
        )

    if not account_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Account-ID header"
        )
    
    # SECURITY FIX: Development/Demo Override - ONLY in non-production
    if not IS_PRODUCTION:
        if api_key.startswith("sk_test_") or api_key == "demo-key":
            logger.warning("[AUTH] Test/demo key used - DEV MODE ONLY")
            return account_id
    else:
        # In production, reject test keys immediately
        if api_key.startswith("sk_test_") or api_key == "demo-key":
            logger.warning("[AUTH] Test key rejected in production!")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Test API keys are not allowed in production"
            )

    # Production API key validation against database
    logger.debug("[AUTH] Validating API key against database...")
    try:
        # Fetch API keys for the account
        res = supabase.table('api_keys').select('id, key_hash, is_active').eq('account_id', account_id).execute()
        keys = res.data

        if not keys:
            logger.warning(f"[AUTH] No API keys found for account")
            raise HTTPException(status_code=403, detail="Invalid API Key")

        is_valid = False
        for k in keys:
            # Skip inactive keys
            if not k.get('is_active', True):
                continue
                
            # Check key hash
            stored_hash = k.get('key_hash') or k.get('key')
            if stored_hash:
                try:
                    if pwd_context.verify(api_key, stored_hash):
                        is_valid = True
                        logger.debug("[AUTH] API key verified successfully")
                        break
                except Exception:
                    # Don't log verification errors in detail (could leak timing info)
                    continue

        if not is_valid:
            logger.warning("[AUTH] API key validation failed")
            raise HTTPException(status_code=403, detail="Invalid API Key")

    except HTTPException:
        raise
    except Exception as e:
        # SECURITY: Don't expose internal errors
        logger.error(f"[AUTH] Database error during authentication")
        raise HTTPException(status_code=403, detail="Authentication failed")

    return account_id
