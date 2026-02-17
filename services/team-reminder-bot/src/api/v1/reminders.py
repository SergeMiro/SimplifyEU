"""
API Routes for Team Reminder Bot — Reminders CRUD + Slack webhook.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Header, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from ...auth.api_key import get_current_account
from ...db.models import ReminderCreate, ReminderUpdate
from ...core import reminder_scheduler
from ...core.context_manager import log_event
from ...core.queue_worker import process_due_reminders

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()


@router.post("/reminders", status_code=201)
@limiter.limit("30/minute")
async def create_reminder(
    request: Request,
    data: ReminderCreate,
    account_id: str = Depends(get_current_account),
    user_id: str = Header("anonymous", alias="X-User-ID"),
):
    """Create a new reminder."""
    try:
        result = await reminder_scheduler.create_reminder(
            team_id=account_id,
            creator_user_id=user_id,
            data=data,
        )

        # Log the event
        await log_event(
            team_id=account_id,
            user_id=user_id,
            event_type="reminder_created",
            event_data={"task_text": data.task_text, "target_user_id": data.target_user_id},
            related_reminder_id=result.get("id"),
        )

        return {"status": "ok", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create reminder: {e}")
        raise HTTPException(status_code=500, detail="Failed to create reminder")


@router.get("/reminders")
@limiter.limit("60/minute")
async def list_reminders(
    request: Request,
    status: Optional[str] = Query(None),
    target_user_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    account_id: str = Depends(get_current_account),
):
    """List reminders with pagination and filters."""
    try:
        result = await reminder_scheduler.list_reminders(
            team_id=account_id,
            status=status,
            target_user_id=target_user_id,
            page=page,
            limit=limit,
        )
        return result
    except Exception as e:
        logger.error(f"Failed to list reminders: {e}")
        raise HTTPException(status_code=500, detail="Failed to list reminders")


@router.get("/reminders/{reminder_id}")
@limiter.limit("60/minute")
async def get_reminder(
    request: Request,
    reminder_id: str,
    account_id: str = Depends(get_current_account),
):
    """Get a single reminder by ID."""
    result = await reminder_scheduler.get_reminder(reminder_id, account_id)
    if not result:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return {"status": "ok", "data": result}


@router.patch("/reminders/{reminder_id}")
@limiter.limit("30/minute")
async def update_reminder(
    request: Request,
    reminder_id: str,
    data: ReminderUpdate,
    account_id: str = Depends(get_current_account),
):
    """Update a reminder."""
    result = await reminder_scheduler.update_reminder(reminder_id, account_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Reminder not found")

    # Log status changes
    if data.status:
        await log_event(
            team_id=account_id,
            user_id=result.get("target_user_id", "unknown"),
            event_type=f"reminder_{data.status}",
            event_data={"task_text": result.get("task_text")},
            related_reminder_id=reminder_id,
        )

    return {"status": "ok", "data": result}


@router.delete("/reminders/{reminder_id}")
@limiter.limit("20/minute")
async def delete_reminder(
    request: Request,
    reminder_id: str,
    account_id: str = Depends(get_current_account),
):
    """Delete a reminder."""
    deleted = await reminder_scheduler.delete_reminder(reminder_id, account_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return {"status": "ok", "message": "Reminder deleted"}


@router.post("/reminders/{reminder_id}/snooze")
@limiter.limit("30/minute")
async def snooze_reminder(
    request: Request,
    reminder_id: str,
    minutes: int = Query(15, ge=1, le=1440),
    account_id: str = Depends(get_current_account),
):
    """Snooze a reminder by N minutes."""
    result = await reminder_scheduler.snooze_reminder(reminder_id, account_id, minutes)
    if not result:
        raise HTTPException(status_code=404, detail="Reminder not found")

    await log_event(
        team_id=account_id,
        user_id=result.get("target_user_id", "unknown"),
        event_type="reminder_snoozed",
        event_data={"minutes": minutes},
        related_reminder_id=reminder_id,
    )

    return {"status": "ok", "data": result}


@router.post("/reminders/process-queue")
@limiter.limit("10/minute")
async def trigger_queue_processing(
    request: Request,
    background_tasks: BackgroundTasks,
    account_id: str = Depends(get_current_account),
):
    """Manually trigger processing of due reminders (for testing/admin)."""
    background_tasks.add_task(process_due_reminders)
    return {"status": "ok", "message": "Queue processing triggered"}


@router.get("/stats")
@limiter.limit("30/minute")
async def get_stats(
    request: Request,
    account_id: str = Depends(get_current_account),
):
    """Get basic stats for the team."""
    from ...core.context_manager import get_user_stats
    from ...db.client import supabase

    try:
        # Count reminders by status
        res = (
            supabase.table("reminders")
            .select("status", count="exact")
            .eq("team_id", account_id)
            .execute()
        )

        stats = {
            "total": res.count or 0,
            "pending": 0,
            "sent": 0,
            "completed": 0,
            "cancelled": 0,
            "failed": 0,
        }

        if res.data:
            for r in res.data:
                st = r.get("status", "")
                if st in stats:
                    stats[st] += 1

        return {"status": "ok", "data": stats}
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get stats")
