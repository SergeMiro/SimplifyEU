"""
Context Manager — Loads and enriches context for reminder messages.

Provides:
- Historical context for a user (past reminders, completion rate)
- Related tasks detection (same project or user)
- Event logging for context history
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select, func

from ..db.session import SessionLocal
from ..db.orm import ContextHistory, Reminder

logger = logging.getLogger(__name__)


async def log_event(
    team_id: str,
    user_id: str,
    event_type: str,
    event_data: dict = None,
    related_reminder_id: Optional[str] = None
) -> dict:
    """Log a context event for future reference."""
    now = datetime.now(timezone.utc)

    try:
        event = ContextHistory(
            team_id=uuid.UUID(team_id),
            user_id=user_id,
            event_type=event_type,
            event_data=event_data or {},
            related_reminder_id=uuid.UUID(related_reminder_id) if related_reminder_id else None,
        )
        with SessionLocal() as session:
            session.add(event)
            session.commit()
            session.refresh(event)
            return {
                "id": str(event.id),
                "team_id": str(event.team_id),
                "user_id": event.user_id,
                "event_type": event.event_type,
                "event_data": event.event_data,
                "related_reminder_id": str(event.related_reminder_id)
                if event.related_reminder_id
                else None,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
    except Exception as e:
        logger.error(f"[CONTEXT] Failed to log event: {e}")
        # Non-critical — don't raise, just log
        return {
            "team_id": team_id,
            "user_id": user_id,
            "event_type": event_type,
            "event_data": event_data or {},
            "related_reminder_id": related_reminder_id,
            "created_at": now.isoformat(),
        }


async def get_user_context(
    team_id: str,
    user_id: str,
    limit: int = 10
) -> dict:
    """
    Get enriched context for a user.

    Returns:
        Dict with recent_events, stats, and related info.
    """
    context = {
        "recent_events": [],
        "stats": {
            "total_reminders": 0,
            "completed": 0,
            "completion_rate": 0.0,
            "pending": 0,
        },
        "related_tasks": [],
    }

    try:
        with SessionLocal() as session:
            stmt = (
                select(ContextHistory)
                .where(
                    ContextHistory.team_id == uuid.UUID(team_id),
                    ContextHistory.user_id == user_id,
                )
                .order_by(ContextHistory.created_at.desc())
                .limit(limit)
            )
            events = session.scalars(stmt).all()
            context["recent_events"] = [
                {
                    "id": str(e.id),
                    "team_id": str(e.team_id),
                    "user_id": e.user_id,
                    "event_type": e.event_type,
                    "event_data": e.event_data,
                    "related_reminder_id": str(e.related_reminder_id)
                    if e.related_reminder_id
                    else None,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in events
            ]

        # Stats
        context["stats"] = await get_user_stats(team_id, user_id)

    except Exception as e:
        logger.error(f"[CONTEXT] Failed to get user context: {e}")

    return context


async def get_user_stats(team_id: str, user_id: str) -> dict:
    """Get reminder completion stats for a user."""
    stats = {
        "total_reminders": 0,
        "completed": 0,
        "completion_rate": 0.0,
        "pending": 0,
        "snoozed": 0,
        "cancelled": 0,
    }

    try:
        with SessionLocal() as session:
            stmt = (
                select(Reminder.status, func.count())
                .where(
                    Reminder.team_id == uuid.UUID(team_id),
                    Reminder.target_user_id == user_id,
                )
                .group_by(Reminder.status)
            )
            rows = session.execute(stmt).all()

        for status_value, count in rows:
            stats["total_reminders"] += count
            if status_value in stats:
                stats[status_value] += count

        if stats["total_reminders"] > 0:
            stats["completion_rate"] = round(
                stats["completed"] / stats["total_reminders"] * 100, 1
            )

    except Exception as e:
        logger.error(f"[CONTEXT] Failed to get user stats: {e}")

    return stats


async def find_related_tasks(
    team_id: str,
    project: Optional[str] = None,
    target_user_id: Optional[str] = None,
    limit: int = 5
) -> List[dict]:
    """Find related pending tasks for context enrichment."""
    related = []

    try:
        with SessionLocal() as session:
            filters = [
                Reminder.team_id == uuid.UUID(team_id),
                Reminder.status == "pending",
            ]
            if project:
                filters.append(Reminder.project == project)
            elif target_user_id:
                filters.append(Reminder.target_user_id == target_user_id)
            else:
                return []

            stmt = (
                select(
                    Reminder.id,
                    Reminder.task_text,
                    Reminder.project,
                    Reminder.priority,
                    Reminder.remind_at,
                    Reminder.status,
                )
                .where(*filters)
                .order_by(Reminder.remind_at.asc())
                .limit(limit)
            )
            rows = session.execute(stmt).all()
            related = [
                {
                    "id": str(row.id),
                    "task_text": row.task_text,
                    "project": row.project,
                    "priority": row.priority,
                    "remind_at": row.remind_at.isoformat() if row.remind_at else None,
                    "status": row.status,
                }
                for row in rows
            ]

    except Exception as e:
        logger.error(f"[CONTEXT] Failed to find related tasks: {e}")

    return related


async def enrich_reminder_message(reminder: dict) -> dict:
    """
    Enrich a reminder with context data for a smarter message.

    Returns a dict with:
    - context_summary: string with user stats
    - related_tasks: list of related pending tasks
    """
    enrichment = {
        "context_summary": "",
        "related_tasks": [],
    }

    team_id = reminder.get("team_id")
    target_user_id = reminder.get("target_user_id")
    project = reminder.get("project")

    if not team_id or not target_user_id:
        return enrichment

    # Get user stats
    stats = await get_user_stats(team_id, target_user_id)

    if stats["total_reminders"] > 0:
        enrichment["context_summary"] = (
            f"✅ Completed {stats['completed']}/{stats['total_reminders']} tasks "
            f"({stats['completion_rate']}% rate)"
        )

    # Find related tasks
    related = await find_related_tasks(
        team_id=team_id,
        project=project,
        target_user_id=target_user_id,
        limit=3,
    )
    # Exclude the current reminder itself
    enrichment["related_tasks"] = [
        r for r in related if r.get("id") != str(reminder.get("id"))
    ]

    return enrichment
