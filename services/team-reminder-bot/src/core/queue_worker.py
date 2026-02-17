"""
Queue Worker — Background poller for due reminders.

Polls the reminders table for entries where remind_at <= now and status = 'pending'.
Sends formatted messages via (mock) Slack/HTTP webhook and handles retries.

In production, this would send via Slack API. For now, it logs + updates status.
"""
import asyncio
import logging
from datetime import datetime, timezone

from ..config import settings
from .reminder_scheduler import get_due_reminders, mark_sent, mark_failed, create_next_recurring
from .context_manager import enrich_reminder_message, log_event
from .slack_formatter import format_reminder_message

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


async def process_due_reminders() -> int:
    """
    Process all due reminders: enrich, format, send, and update status.

    Returns:
        Number of reminders processed.
    """
    due = await get_due_reminders(limit=50)

    if not due:
        return 0

    logger.info(f"[WORKER] Found {len(due)} due reminders")
    processed = 0

    for reminder in due:
        reminder_id = reminder.get("id")
        retry_count = reminder.get("retry_count", 0)

        try:
            # Enrich with context
            enrichment = await enrich_reminder_message(reminder)

            # Format message
            message = format_reminder_message(
                reminder,
                context_summary=enrichment.get("context_summary"),
                related_tasks=enrichment.get("related_tasks"),
            )

            # Send message (mock: in real prod, call Slack API)
            success = await _send_slack_message(
                user_id=reminder.get("target_user_id"),
                message=message,
            )

            if success:
                await mark_sent(reminder_id)
                await log_event(
                    team_id=reminder.get("team_id"),
                    user_id=reminder.get("target_user_id"),
                    event_type="reminder_sent",
                    event_data={"task_text": reminder.get("task_text")},
                    related_reminder_id=reminder_id,
                )

                # Handle recurring reminders
                if reminder.get("repeat"):
                    await create_next_recurring(reminder)

                processed += 1
            else:
                # Retry logic
                new_retry_count = retry_count + 1
                if new_retry_count >= MAX_RETRIES:
                    await mark_failed(reminder_id, "Max retries exceeded", new_retry_count)
                else:
                    # Increment retry count for next poll
                    from ..db.client import supabase
                    supabase.table("reminders").update({
                        "retry_count": new_retry_count,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }).eq("id", reminder_id).execute()
                    logger.warning(
                        f"[WORKER] Retry {new_retry_count}/{MAX_RETRIES} for reminder {reminder_id}"
                    )

        except Exception as e:
            logger.error(f"[WORKER] Error processing reminder {reminder_id}: {e}")
            new_retry_count = retry_count + 1
            if new_retry_count >= MAX_RETRIES:
                await mark_failed(reminder_id, str(e), new_retry_count)

    return processed


async def _send_slack_message(user_id: str, message: dict) -> bool:
    """
    Send a message to a Slack user.

    In production, this calls the Slack API.
    In development, it logs the message.
    """
    if not settings.SLACK_BOT_TOKEN:
        logger.info(
            f"[WORKER] (Mock) Would send to {user_id}: {message.get('text', 'No text')}"
        )
        return True

    try:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={
                    "channel": user_id,
                    "text": message.get("text", ""),
                    "blocks": message.get("blocks", []),
                },
                timeout=10.0,
            )

            data = response.json()
            if data.get("ok"):
                logger.info(f"[WORKER] Sent reminder to {user_id}")
                return True
            else:
                logger.error(f"[WORKER] Slack API error: {data.get('error', 'unknown')}")
                return False

    except Exception as e:
        logger.error(f"[WORKER] Failed to send Slack message: {e}")
        return False


async def run_worker_loop():
    """
    Main worker loop — polls for due reminders periodically.
    Run this as a background task or separate process.
    """
    interval = settings.QUEUE_POLL_INTERVAL_SECONDS
    logger.info(f"[WORKER] Starting queue worker (poll interval: {interval}s)")

    while True:
        try:
            processed = await process_due_reminders()
            if processed > 0:
                logger.info(f"[WORKER] Processed {processed} reminders")
        except Exception as e:
            logger.error(f"[WORKER] Worker loop error: {e}")

        await asyncio.sleep(interval)
