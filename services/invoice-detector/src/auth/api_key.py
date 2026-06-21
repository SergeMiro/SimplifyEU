import logging
import secrets

from fastapi import Header, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader

from ..config import settings

logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_account(
    api_key: str = Security(api_key_header),
    account_id: str = Header(..., alias="X-Account-ID"),
) -> str:
    """
    Validate the service X-API-Key and return the account_id (tenant scope).

    The web app calls this service with a shared service key in X-API-Key and
    the tenant id in X-Account-ID.

    SECURITY NOTES:
    - Test/demo keys are ONLY honored in non-production environments.
    - The configured SERVICE_API_KEY is compared in constant time.
    - API keys are NEVER logged.
    """
    logger.debug("[AUTH] Service-key request for account: %s", account_id)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key",
        )

    if not account_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Account-ID header",
        )

    is_test_key = api_key.startswith("sk_test_") or api_key == "demo-key"

    # Development/demo override - ONLY in non-production.
    if not settings.is_production:
        if is_test_key:
            logger.warning("[AUTH] Test/demo key used - DEV MODE ONLY")
            return account_id
    elif is_test_key:
        logger.warning("[AUTH] Test key rejected in production!")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test API keys are not allowed in production",
        )

    # Validate against the configured service key (constant-time compare).
    if not settings.SERVICE_API_KEY:
        logger.error("[AUTH] SERVICE_API_KEY not configured")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API Key")

    if not secrets.compare_digest(api_key, settings.SERVICE_API_KEY):
        logger.warning("[AUTH] Service API key validation failed")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API Key")

    return account_id
