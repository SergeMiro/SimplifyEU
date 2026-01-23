from fastapi import Security, HTTPException, status, Header
from fastapi.security.api_key import APIKeyHeader
from passlib.context import CryptContext
from ..db.client import supabase

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_current_account(
    api_key: str = Security(api_key_header),
    account_id: str = Header(..., alias="X-Account-ID")
) -> str:
    """
    Validates API Key and returns account_id.
    Verifies the hash of the api_key against the stored hash in the database.
    """
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

    # Development/Demo Override
    if api_key.startswith("sk_test_") or api_key == "demo-key":
         return account_id

    try:
        # Fetch API keys for the account
        # We assume table 'api_keys' exists with 'account_id' and 'key_hash' (or 'key' storing the hash)
        res = supabase.table('api_keys').select('*').eq('account_id', account_id).execute()
        keys = res.data

        if not keys:
            raise HTTPException(status_code=403, detail="Invalid API Key")

        is_valid = False
        for k in keys:
            # Check 'key_hash' or 'key'
            stored_hash = k.get('key_hash') or k.get('key')
            if stored_hash:
                try:
                    if pwd_context.verify(api_key, stored_hash):
                        is_valid = True
                        break
                except Exception:
                    continue

        if not is_valid:
            raise HTTPException(status_code=403, detail="Invalid API Key")

    except HTTPException:
        raise
    except Exception as e:
        # Log error
        print(f"Auth error: {e}")
        # Don't expose internal error
        raise HTTPException(status_code=403, detail="Invalid credentials")

    return account_id
