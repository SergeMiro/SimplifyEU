"""
API Routes for Teams management.
"""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from ...auth.api_key import get_current_account
from ...db.client import supabase
from ...db.models import TeamCreate

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()


@router.post("/teams", status_code=201)
@limiter.limit("10/minute")
async def create_team(
    request: Request,
    data: TeamCreate,
    account_id: str = Depends(get_current_account),
):
    """Register a new team / workspace."""
    now = datetime.now(timezone.utc)
    team_id = str(uuid.uuid4())

    record = {
        "id": team_id,
        "slack_team_id": data.slack_team_id,
        "name": data.name,
        "subscription_tier": "free",
        "reminders_count": 0,
        "max_reminders": 50,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    try:
        # Check for existing team with same slack_team_id
        existing = (
            supabase.table("teams")
            .select("id")
            .eq("slack_team_id", data.slack_team_id)
            .execute()
        )
        if existing.data:
            raise HTTPException(status_code=409, detail="Team already registered")

        res = supabase.table("teams").insert(record).execute()
        return {"status": "ok", "data": res.data[0] if res.data else record}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create team: {e}")
        raise HTTPException(status_code=500, detail="Failed to create team")


@router.get("/teams/{team_id}")
@limiter.limit("30/minute")
async def get_team(
    request: Request,
    team_id: str,
    account_id: str = Depends(get_current_account),
):
    """Get team details."""
    try:
        res = (
            supabase.table("teams")
            .select("*")
            .eq("id", team_id)
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=404, detail="Team not found")
        return {"status": "ok", "data": res.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get team: {e}")
        raise HTTPException(status_code=500, detail="Failed to get team")
