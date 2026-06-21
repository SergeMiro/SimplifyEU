"""
Better Auth JWT validation against the web app's JWKS endpoint.

The web app authenticates calls to this service with a Better Auth JWT
(`Authorization: Bearer <jwt>`), signed with the key set served at
BETTER_AUTH_JWKS_URL (the web's `/api/auth/jwks`). The Better Auth `jwt`
plugin defaults to EdDSA (Ed25519), so we verify with that algorithm.

Key handling: `PyJWKClient` fetches and CACHES the JWKS (default lifespan
300s) and refreshes on a cache miss / kid rotation, so we are NOT fetching
keys per request. A single module-level client is reused across requests.

The JWT `sub` claim is the user id (uuid). `get_current_user` validates the
signature + expiry and returns that user id.
"""
import logging
from urllib.parse import urlparse

import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.security.api_key import APIKeyHeader
from jwt import PyJWKClient

from ..config import settings

logger = logging.getLogger(__name__)

# Algorithms we accept. Better Auth's jwt() plugin defaults to EdDSA (Ed25519).
_ALLOWED_ALGORITHMS = ["EdDSA"]

# Bearer scheme. auto_error=False so we can return our own 401 messages and so
# the service-key path can still be checked independently by callers.
bearer_scheme = HTTPBearer(auto_error=False)

# Module-level JWKS client => keys are cached and refreshed, not re-fetched per
# request. Lazily constructed so importing the module never does network I/O.
_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        if not settings.BETTER_AUTH_JWKS_URL:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="JWKS URL not configured",
            )
        # cache_keys=True keeps resolved signing keys in memory between calls;
        # lifespan caps how long the JWKS document is trusted before refetch.
        _jwks_client = PyJWKClient(
            settings.BETTER_AUTH_JWKS_URL,
            cache_keys=True,
            lifespan=settings.JWKS_CACHE_SECONDS,
        )
    return _jwks_client


def _expected_audience() -> str | None:
    """Better Auth stamps `aud` = the baseURL ORIGIN (e.g. https://app.example.com),
    which equals the origin of BETTER_AUTH_JWKS_URL. Return that origin so PyJWT can
    verify the audience. If it can't be derived, callers skip aud verification."""
    parsed = urlparse(settings.BETTER_AUTH_JWKS_URL or "")
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return None


def verify_jwt(token: str) -> dict:
    """
    Verify a Better Auth JWT against the cached JWKS and return its claims.

    Raises HTTPException(401) on any validation failure.
    """
    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        # Better Auth sets `aud` to the baseURL origin; PyJWT verifies aud by default,
        # so we MUST pass the expected audience (else every real token => 401).
        audience = _expected_audience()
        options = {"require": ["exp", "sub"], "verify_exp": True}
        if audience is None:
            options["verify_aud"] = False
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=_ALLOWED_ALGORITHMS,
            audience=audience,
            options=options,
        )
        return claims
    except HTTPException:
        raise
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
        )
    except jwt.PyJWTError as exc:
        logger.warning("[AUTH] JWT validation failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
    except Exception:
        # e.g. JWKS endpoint unreachable / malformed key set.
        logger.error("[AUTH] JWKS resolution error")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    """
    FastAPI dependency: validate the Bearer Better Auth JWT and return the
    user id (the `sub` claim).
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    claims = verify_jwt(credentials.credentials)
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
        )
    return user_id


# Re-declare the X-API-Key header here so this combined dependency is
# self-contained and reusable across services.
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_jwt(
    api_key: str = Security(_api_key_header),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str | None:
    """
    Enforce the Better Auth Bearer JWT for real requests and return the user id.

    Dev ergonomics: in non-production, requests using a test/demo service key
    (`sk_test_*` / `demo-key`) skip JWT validation so local tooling and the test
    suite keep working. Every other request MUST present a valid JWT.
    """
    is_test_key = bool(api_key) and (api_key.startswith("sk_test_") or api_key == "demo-key")
    if not settings.is_production and is_test_key:
        return None

    return await get_current_user(credentials)
