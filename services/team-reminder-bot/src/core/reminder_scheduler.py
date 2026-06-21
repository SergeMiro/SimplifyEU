"""
Reminder Scheduler — CRUD operations for reminders via SQLAlchemy.
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from sqlalchemy import select, func

from ..db.session import SessionLocal
from ..db.orm import Reminder
from ..db.models import ReminderCreate, ReminderUpdate
from .time_parser import parse_time, calculate_delay_seconds

logger = logging.getLogger(__name__)


def _to_dict(reminder: Reminder) -> dict:
    """Serialize a Reminder ORM row to a plain dict (timestamps as ISO strings)."""
    return {
        "id": str(reminder.id),
        "team_id": str(reminder.team_id),
        "creator_user_id": reminder.creator_user_id,
        "target_user_id": reminder.target_user_id,
        "task_text": reminder.task_text,
        "context": reminder.context,
        "project": reminder.project,
        "priority": reminder.priority,
        "remind_at": reminder.remind_at.isoformat() if reminder.remind_at else None,
        "status": reminder.status,
        "repeat": reminder.repeat,
        "parent_reminder_id": str(reminder.parent_reminder_id)
        if reminder.parent_reminder_id
        else None,
        "sent_at": reminder.sent_at.isoformat() if reminder.sent_at else None,
        "completed_at": reminder.completed_at.isoformat() if reminder.completed_at else None,
        "snooze_count": reminder.snooze_count,
        "retry_count": reminder.retry_count,
        "error_message": reminder.error_message,
        "created_at": reminder.created_at.isoformat() if reminder.created_at else None,
        "updated_at": reminder.updated_at.isoformat() if reminder.updated_at else None,
    }


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

    reminder = Reminder(
        team_id=uuid.UUID(team_id),
        creator_user_id=creator_user_id,
        target_user_id=data.target_user_id,
        task_text=data.task_text,
        context=data.context,
        project=data.project,
        priority=data.priority,
        remind_at=remind_at,
        status="pending",
        repeat=data.repeat,
        snooze_count=0,
        retry_count=0,
    )

    try:
        with SessionLocal() as session:
            session.add(reminder)
            session.commit()
            session.refresh(reminder)
            logger.info(
                f"[SCHEDULER] Created reminder {reminder.id} for user {data.target_user_id}"
            )
            return _to_dict(reminder)
    except Exception as e:
        logger.error(f"[SCHEDULER] Failed to create reminder: {e}")
        raise


async def get_reminder(reminder_id: str, team_id: str) -> Optional[dict]:
    """Get a single reminder by ID, scoped to team."""
    try:
        with SessionLocal() as session:
            stmt = select(Reminder).where(
                Reminder.id == uuid.UUID(reminder_id),
                Reminder.team_id == uuid.UUID(team_id),
            )
            reminder = session.scalars(stmt).first()
            return _to_dict(reminder) if reminder else None
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
        with SessionLocal() as session:
            filters = [Reminder.team_id == uuid.UUID(team_id)]
            if status:
                filters.append(Reminder.status == status)
            if target_user_id:
                filters.append(Reminder.target_user_id == target_user_id)

            total = session.scalar(
                select(func.count()).select_from(Reminder).where(*filters)
            ) or 0

            offset = (page - 1) * limit
            stmt = (
                select(Reminder)
                .where(*filters)
                .order_by(Reminder.remind_at.asc())
                .offset(offset)
                .limit(limit)
            )
            rows = session.scalars(stmt).all()

            return {
                "data": [_to_dict(r) for r in rows],
                "total": total,
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

    try:
        with SessionLocal() as session:
            stmt = select(Reminder).where(
                Reminder.id == uuid.UUID(reminder_id),
                Reminder.team_id == uuid.UUID(team_id),
            )
            reminder = session.scalars(stmt).first()
            if not reminder:
                return None

            for field, value in update_data.items():
                setattr(reminder, field, value)
            reminder.updated_at = datetime.now(timezone.utc)

            session.commit()
            session.refresh(reminder)
            logger.info(f"[SCHEDULER] Updated reminder {reminder_id}")
            return _to_dict(reminder)
    except Exception as e:
        logger.error(f"[SCHEDULER] Failed to update reminder {reminder_id}: {e}")
        raise


async def delete_reminder(reminder_id: str, team_id: str) -> bool:
    """Delete a reminder."""
    try:
        with SessionLocal() as session:
            stmt = select(Reminder).where(
                Reminder.id == uuid.UUID(reminder_id),
                Reminder.team_id == uuid.UUID(team_id),
            )
            reminder = session.scalars(stmt).first()
            if not reminder:
                return False

            session.delete(reminder)
            session.commit()
            logger.info(f"[SCHEDULER] Deleted reminder {reminder_id}")
            return True
    except Exception as e:
        logger.error(f"[SCHEDULER] Failed to delete reminder {reminder_id}: {e}")
        raise


async def snooze_reminder(
    reminder_id: str,
    team_id: str,
    snooze_minutes: int = 15
) -> Optional[dict]:
    """Snooze a reminder by N minutes."""
    now = datetime.now(timezone.utc)
    new_remind_at = now + timedelta(minutes=snooze_minutes)

    try:
        with SessionLocal() as session:
            stmt = select(Reminder).where(
                Reminder.id == uuid.UUID(reminder_id),
                Reminder.team_id == uuid.UUID(team_id),
            )
            reminder = session.scalars(stmt).first()
            if not reminder:
                return None

            reminder.remind_at = new_remind_at
            reminder.status = "pending"
            reminder.snooze_count = (reminder.snooze_count or 0) + 1
            reminder.updated_at = now

            session.commit()
            session.refresh(reminder)
            logger.info(f"[SCHEDULER] Snoozed reminder {reminder_id} for {snooze_minutes} min")
            return _to_dict(reminder)
    except Exception as e:
        logger.error(f"[SCHEDULER] Failed to snooze reminder {reminder_id}: {e}")
        raise


async def get_due_reminders(limit: int = 50) -> List[dict]:
    """Get reminders that are due for sending (remind_at <= now, status = pending)."""
    now = datetime.now(timezone.utc)
    try:
        with SessionLocal() as session:
            stmt = (
                select(Reminder)
                .where(Reminder.status == "pending", Reminder.remind_at <= now)
                .order_by(Reminder.remind_at.asc())
                .limit(limit)
            )
            rows = session.scalars(stmt).all()
            return [_to_dict(r) for r in rows]
    except Exception as e:
        logger.error(f"[SCHEDULER] Failed to get due reminders: {e}")
        raise


async def mark_sent(reminder_id: str) -> None:
    """Mark a reminder as sent."""
    now = datetime.now(timezone.utc)
    try:
        with SessionLocal() as session:
            reminder = session.get(Reminder, uuid.UUID(reminder_id))
            if reminder:
                reminder.status = "sent"
                reminder.sent_at = now
                reminder.updated_at = now
                session.commit()
        logger.info(f"[SCHEDULER] Marked reminder {reminder_id} as sent")
    except Exception as e:
        logger.error(f"[SCHEDULER] Failed to mark sent {reminder_id}: {e}")
        raise


async def mark_failed(reminder_id: str, error: str, retry_count: int) -> None:
    """Mark a reminder as failed after exhausting retries."""
    now = datetime.now(timezone.utc)
    try:
        with SessionLocal() as session:
            reminder = session.get(Reminder, uuid.UUID(reminder_id))
            if reminder:
                reminder.status = "failed"
                reminder.error_message = error
                reminder.retry_count = retry_count
                reminder.updated_at = now
                session.commit()
        logger.warning(f"[SCHEDULER] Marked reminder {reminder_id} as failed: {error}")
    except Exception as e:
        logger.error(f"[SCHEDULER] Failed to mark failed {reminder_id}: {e}")
        raise


async def increment_retry(reminder_id: str, retry_count: int) -> None:
    """Persist an incremented retry counter for a reminder."""
    now = datetime.now(timezone.utc)
    try:
        with SessionLocal() as session:
            reminder = session.get(Reminder, uuid.UUID(reminder_id))
            if reminder:
                reminder.retry_count = retry_count
                reminder.updated_at = now
                session.commit()
    except Exception as e:
        logger.error(f"[SCHEDULER] Failed to increment retry {reminder_id}: {e}")
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

    new_reminder = Reminder(
        team_id=uuid.UUID(reminder["team_id"]),
        creator_user_id=reminder["creator_user_id"],
        target_user_id=reminder["target_user_id"],
        task_text=reminder["task_text"],
        context=reminder.get("context"),
        project=reminder.get("project"),
        priority=reminder.get("priority", "medium"),
        remind_at=next_remind_at,
        status="pending",
        repeat=repeat,
        parent_reminder_id=uuid.UUID(reminder["id"]),
        snooze_count=0,
        retry_count=0,
    )

    try:
        with SessionLocal() as session:
            session.add(new_reminder)
            session.commit()
            session.refresh(new_reminder)
            logger.info(
                f"[SCHEDULER] Created next recurring reminder {new_reminder.id} from {reminder['id']}"
            )
            return _to_dict(new_reminder)
    except Exception as e:
        logger.error(f"[SCHEDULER] Failed to create next recurring: {e}")
        raise
