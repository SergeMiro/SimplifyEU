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
    print(f"[AUTH] Incoming request - API Key: {api_key[:10]}... Account ID: {account_id}")
    
    # Development/Demo Override - CHECK THIS FIRST to avoid DB calls
    if api_key and (api_key.startswith("sk_test_") or api_key == "demo-key"):
        print(f"[AUTH] Using demo/test key, bypassing database validation")
        if not account_id:
            raise HTTPException(
                 status_code=status.HTTP_400_BAD_REQUEST,
                 detail="Missing X-Account-ID header"
            )
        return account_id
    
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

    print(f"[AUTH] Checking production API key against database...")
    try:
        # Fetch API keys for the account
        # We assume table 'api_keys' exists with 'account_id' and 'key_hash' (or 'key' storing the hash)
        res = supabase.table('api_keys').select('*').eq('account_id', account_id).execute()
        keys = res.data

        if not keys:
            print(f"[AUTH] No API keys found for account {account_id}")
            raise HTTPException(status_code=403, detail="Invalid API Key")

        is_valid = False
        for k in keys:
            # Check 'key_hash' or 'key'
            stored_hash = k.get('key_hash') or k.get('key')
            if stored_hash:
                try:
                    if pwd_context.verify(api_key, stored_hash):
                        is_valid = True
                        print(f"[AUTH] API key verified successfully")
                        break
                except Exception as verify_err:
                    print(f"[AUTH] Verify error: {verify_err}")
                    continue

        if not is_valid:
            print(f"[AUTH] API key validation failed")
            raise HTTPException(status_code=403, detail="Invalid API Key")

    except HTTPException:
        raise
    except Exception as e:
        # Log error
        print(f"[AUTH] Database error: {e}")
        # Don't expose internal error
        raise HTTPException(status_code=403, detail="Invalid credentials")

    return account_id
