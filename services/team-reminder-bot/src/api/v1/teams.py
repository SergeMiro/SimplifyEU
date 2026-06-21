"""
API Routes for Teams management.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...auth.api_key import get_current_account
from ...db.session import get_db
from ...db.orm import Team
from ...db.models import TeamCreate

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()


def _team_to_dict(team: Team) -> dict:
    return {
        "id": str(team.id),
        "slack_team_id": team.slack_team_id,
        "name": team.name,
        "subscription_tier": team.subscription_tier,
        "reminders_count": team.reminders_count,
        "max_reminders": team.max_reminders,
        "created_at": team.created_at.isoformat() if team.created_at else None,
        "updated_at": team.updated_at.isoformat() if team.updated_at else None,
    }


@router.post("/teams", status_code=201)
@limiter.limit("10/minute")
async def create_team(
    request: Request,
    data: TeamCreate,
    account_id: str = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """Register a new team / workspace."""
    try:
        existing = db.scalars(
            select(Team).where(Team.slack_team_id == data.slack_team_id)
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="Team already registered")

        team = Team(slack_team_id=data.slack_team_id, name=data.name)
        db.add(team)
        db.commit()
        db.refresh(team)
        return {"status": "ok", "data": _team_to_dict(team)}
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
    db: Session = Depends(get_db),
):
    """Get team details."""
    try:
        team = db.get(Team, team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        return {"status": "ok", "data": _team_to_dict(team)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get team: {e}")
        raise HTTPException(status_code=500, detail="Failed to get team")
