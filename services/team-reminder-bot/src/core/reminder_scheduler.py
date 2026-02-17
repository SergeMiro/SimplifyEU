"""
Reminder Scheduler — CRUD operations for reminders in Supabase.
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from ..db.client import supabase
from ..db.models import Reminder, ReminderCreate, ReminderUpdate
from .time_parser import parse_time, calculate_delay_seconds

logger = logging.getLogger(__name__)


async def create_reminder(
    team_id: str,
    creator_user_id: str,
    data: ReminderCreate
) -> dict:
    """
    Create a new reminder and schedule it for delivery.

    Args:
        team_id: Team / account ID.
        creator_user_id: The user creating the reminder.
        data: Reminder creation payload.

    Returns:
        The created reminder record.
    """
    # Resolve remind_at
    remind_at = data.remind_at
    if not remind_at and data.remind_at_text:
        remind_at = parse_time(data.remind_at_text)
        if not remind_at:
            raise ValueError(f"Could not parse time expression: '{data.remind_at_text}'")

    if not remind_at:
        raise ValueError("Either remind_at or remind_at_text must be provided")

    now = datetime.now(timezone.utc)
    if remind_at.tzinfo is None:
        remind_at = remind_at.replace(tzinfo=timezone.utc)

    if remind_at <= now:
        raise ValueError("Reminder time must be in the future")

    reminder_id = str(uuid.uuid4())

    record = {
        "id": reminder_id,
        "team_id": team_id,
        "creator_user_id": creator_user_id,
        "target_user_id": data.target_user_id,
        "task_text": data.task_text,
        "context": data.context,
        "project": data.project,
        "priority": data.priority,
        "remind_at": remind_at.isoformat(),
        "status": "pending",
        "repeat": data.repeat,
        "snooze_count": 0,
        "retry_count": 0,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    try:
        res = supabase.table("reminders").insert(record).execute()
        logger.info(f"[SCHEDULER] Created reminder {reminder_id} for user {data.target_user_id}")
        return res.data[0] if res.data else record
    except Exception as e:
        logger.error(f"[SCHEDULER] Failed to create reminder: {e}")
        raise


async def get_reminder(reminder_id: str, team_id: str) -> Optional[dict]:
    """Get a single reminder by ID, scoped to team."""
    try:
        res = (
            supabase.table("reminders")
            .select("*")
            .eq("id", reminder_id)
            .eq("team_id", team_id)
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error(f"[SCHEDULER] Failed to get reminder {reminder_id}: {e}")
        raise


async def list_reminders(
    team_id: str,
    status: Optional[str] = None,
    target_user_id: Optional[str] = None,
    page: int = 1,
    limit: int = 20
) -> dict:
    """List reminders with pagination and filters."""
    try:
        query = supabase.table("reminders").select("*", count="exact").eq("team_id", team_id)

        if status:
            query = query.eq("status", status)
        if target_user_id:
            query = query.eq("target_user_id", target_user_id)

        offset = (page - 1) * limit
        query = query.order("remind_at", desc=False).range(offset, offset + limit - 1)

        res = query.execute()

        return {
            "data": res.data or [],
            "total": res.count or 0,
            "page": page,
            "limit": limit,
        }
    except Exception as e:
        logger.error(f"[SCHEDULER] Failed to list reminders: {e}")
        raise


async def update_reminder(reminder_id: str, team_id: str, data: ReminderUpdate) -> Optional[dict]:
    """Update a reminder's fields."""
    update_data = data.model_dump(exclude_none=True)
    if not update_data:
        return await get_reminder(reminder_id, team_id)

    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    try:
        res = (
            supabase.table("reminders")
            .update(update_data)
            .eq("id", reminder_id)
            .eq("team_id", team_id)
            .execute()
        )
        if res.data:
            logger.info(f"[SCHEDULER] Updated reminder {reminder_id}")
            return res.data[0]
        return None
    except Exception as e:
        logger.error(f"[SCHEDULER] Failed to update reminder {reminder_id}: {e}")
        raise


async def delete_reminder(reminder_id: str, team_id: str) -> bool:
    """Delete a reminder."""
    try:
        res = (
            supabase.table("reminders")
            .delete()
            .eq("id", reminder_id)
            .eq("team_id", team_id)
            .execute()
        )
        deleted = bool(res.data)
        if deleted:
            logger.info(f"[SCHEDULER] Deleted reminder {reminder_id}")
        return deleted
    except Exception as e:
        logger.error(f"[SCHEDULER] Failed to delete reminder {reminder_id}: {e}")
        raise


async def snooze_reminder(
    reminder_id: str,
    team_id: str,
    snooze_minutes: int = 15
) -> Optional[dict]:
    """Snooze a reminder by N minutes."""
    reminder = await get_reminder(reminder_id, team_id)
    if not reminder:
        return None

    now = datetime.now(timezone.utc)
    new_remind_at = now + timedelta(minutes=snooze_minutes)

    update_data = {
        "remind_at": new_remind_at.isoformat(),
        "status": "pending",
        "snooze_count": reminder.get("snooze_count", 0) + 1,
        "updated_at": now.isoformat(),
    }

    try:
        res = (
            supabase.table("reminders")
            .update(update_data)
            .eq("id", reminder_id)
            .eq("team_id", team_id)
            .execute()
        )
        if res.data:
            logger.info(f"[SCHEDULER] Snoozed reminder {reminder_id} for {snooze_minutes} min")
            return res.data[0]
        return None
    except Exception as e:
        logger.error(f"[SCHEDULER] Failed to snooze reminder {reminder_id}: {e}")
        raise


async def get_due_reminders(limit: int = 50) -> List[dict]:
    """Get reminders that are due for sending (remind_at <= now, status = pending)."""
    now = datetime.now(timezone.utc)
    try:
        res = (
            supabase.table("reminders")
            .select("*")
            .eq("status", "pending")
            .lte("remind_at", now.isoformat())
            .order("remind_at", desc=False)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception as e:
        logger.error(f"[SCHEDULER] Failed to get due reminders: {e}")
        raise


async def mark_sent(reminder_id: str) -> None:
    """Mark a reminder as sent."""
    now = datetime.now(timezone.utc)
    try:
        supabase.table("reminders").update({
            "status": "sent",
            "sent_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }).eq("id", reminder_id).execute()
        logger.info(f"[SCHEDULER] Marked reminder {reminder_id} as sent")
    except Exception as e:
        logger.error(f"[SCHEDULER] Failed to mark sent {reminder_id}: {e}")
        raise


async def mark_failed(reminder_id: str, error: str, retry_count: int) -> None:
    """Mark a reminder as failed after exhausting retries."""
    now = datetime.now(timezone.utc)
    try:
        supabase.table("reminders").update({
            "status": "failed",
            "error_message": error,
            "retry_count": retry_count,
            "updated_at": now.isoformat(),
        }).eq("id", reminder_id).execute()
        logger.warning(f"[SCHEDULER] Marked reminder {reminder_id} as failed: {error}")
    except Exception as e:
        logger.error(f"[SCHEDULER] Failed to mark failed {reminder_id}: {e}")
        raise


async def create_next_recurring(reminder: dict) -> Optional[dict]:
    """Create the next occurrence for a recurring reminder."""
    repeat = reminder.get("repeat")
    if not repeat:
        return None

    remind_at_str = reminder.get("remind_at")
    if not remind_at_str:
        return None

    remind_at = datetime.fromisoformat(remind_at_str)
    if remind_at.tzinfo is None:
        remind_at = remind_at.replace(tzinfo=timezone.utc)

    delta_map = {
        "daily": timedelta(days=1),
        "weekly": timedelta(weeks=1),
        "biweekly": timedelta(weeks=2),
        "monthly": timedelta(days=30),
    }
    delta = delta_map.get(repeat)
    if not delta:
        return None

    next_remind_at = remind_at + delta
    now = datetime.now(timezone.utc)

    # Ensure next occurrence is in the future
    while next_remind_at <= now:
        next_remind_at += delta

    next_id = str(uuid.uuid4())
    record = {
        "id": next_id,
        "team_id": reminder["team_id"],
        "creator_user_id": reminder["creator_user_id"],
        "target_user_id": reminder["target_user_id"],
        "task_text": reminder["task_text"],
        "context": reminder.get("context"),
        "project": reminder.get("project"),
        "priority": reminder.get("priority", "medium"),
        "remind_at": next_remind_at.isoformat(),
        "status": "pending",
        "repeat": repeat,
        "parent_reminder_id": reminder["id"],
        "snooze_count": 0,
        "retry_count": 0,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    try:
        res = supabase.table("reminders").insert(record).execute()
        logger.info(f"[SCHEDULER] Created next recurring reminder {next_id} from {reminder['id']}")
        return res.data[0] if res.data else record
    except Exception as e:
        logger.error(f"[SCHEDULER] Failed to create next recurring: {e}")
        raise
