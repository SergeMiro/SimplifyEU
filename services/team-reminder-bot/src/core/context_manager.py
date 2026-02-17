"""
Context Manager — Loads and enriches context for reminder messages.

Provides:
- Historical context for a user (past reminders, completion rate)
- Related tasks detection (same project or user)
- Event logging for context history
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from ..db.client import supabase

logger = logging.getLogger(__name__)


async def log_event(
    team_id: str,
    user_id: str,
    event_type: str,
    event_data: dict = None,
    related_reminder_id: Optional[str] = None
) -> dict:
    """Log a context event for future reference."""
    event_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    record = {
        "id": event_id,
        "team_id": team_id,
        "user_id": user_id,
        "event_type": event_type,
        "event_data": event_data or {},
        "related_reminder_id": related_reminder_id,
        "created_at": now.isoformat(),
    }

    try:
        res = supabase.table("context_history").insert(record).execute()
        return res.data[0] if res.data else record
    except Exception as e:
        logger.error(f"[CONTEXT] Failed to log event: {e}")
        # Non-critical — don't raise, just log
        return record


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
        # Recent events
        events_res = (
            supabase.table("context_history")
            .select("*")
            .eq("team_id", team_id)
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        context["recent_events"] = events_res.data or []

        # Stats
        stats = await get_user_stats(team_id, user_id)
        context["stats"] = stats

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
        # Count all reminders for this user
        all_res = (
            supabase.table("reminders")
            .select("status", count="exact")
            .eq("team_id", team_id)
            .eq("target_user_id", user_id)
            .execute()
        )
        stats["total_reminders"] = all_res.count or 0

        if all_res.data:
            for r in all_res.data:
                st = r.get("status")
                if st == "completed":
                    stats["completed"] += 1
                elif st == "pending":
                    stats["pending"] += 1
                elif st == "snoozed":
                    stats["snoozed"] += 1
                elif st == "cancelled":
                    stats["cancelled"] += 1

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
        query = (
            supabase.table("reminders")
            .select("id, task_text, project, priority, remind_at, status")
            .eq("team_id", team_id)
            .eq("status", "pending")
        )

        if project:
            query = query.eq("project", project)
        elif target_user_id:
            query = query.eq("target_user_id", target_user_id)
        else:
            return []

        query = query.order("remind_at", desc=False).limit(limit)
        res = query.execute()
        related = res.data or []

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
