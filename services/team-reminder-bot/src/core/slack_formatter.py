"""
Slack Block Kit message formatter for reminder notifications.

Generates rich, interactive Slack messages with:
- Priority color coding
- Action buttons (Done / Snooze / Cancel)
- Context sections (related tasks, user stats)
"""
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

PRIORITY_EMOJI = {
    "low": "🟢",
    "medium": "🔵",
    "high": "🟠",
    "urgent": "🔴",
}

PRIORITY_COLOR = {
    "low": "#36a64f",
    "medium": "#2196F3",
    "high": "#FF9800",
    "urgent": "#F44336",
}


def format_reminder_message(
    reminder: dict,
    context_summary: Optional[str] = None,
    related_tasks: Optional[List[dict]] = None,
) -> dict:
    """
    Format a reminder as a Slack Block Kit message.

    Args:
        reminder: Reminder record dict.
        context_summary: Optional stats string.
        related_tasks: Optional list of related tasks.

    Returns:
        Dict with 'text' (fallback) and 'blocks' (Block Kit payload).
    """
    priority = reminder.get("priority", "medium")
    emoji = PRIORITY_EMOJI.get(priority, "🔵")
    task_text = reminder.get("task_text", "No description")
    context = reminder.get("context")
    project = reminder.get("project")
    reminder_id = reminder.get("id", "unknown")

    # Fallback text
    fallback_text = f"{emoji} Reminder: {task_text}"

    blocks = []

    # Header section
    blocks.append({
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": f"{emoji} Reminder",
            "emoji": True,
        }
    })

    # Task description
    task_section = f"*{task_text}*"
    if project:
        task_section += f"\n📁 Project: _{project}_"
    if context:
        task_section += f"\n📝 Context: {context}"

    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": task_section,
        }
    })

    # Priority badge
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"Priority: *{priority.upper()}* {emoji}  |  Snooze count: {reminder.get('snooze_count', 0)}",
            }
        ]
    })

    # Context summary (user stats)
    if context_summary:
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": context_summary,
                }
            ]
        })

    # Related tasks
    if related_tasks:
        related_text = "💡 *Related pending tasks:*\n"
        for rt in related_tasks[:3]:
            rt_priority = PRIORITY_EMOJI.get(rt.get("priority", "medium"), "🔵")
            related_text += f"  {rt_priority} {rt.get('task_text', 'Unnamed task')}\n"

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": related_text,
            }
        })

    # Action buttons
    blocks.append({"type": "divider"})
    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "✅ Done", "emoji": True},
                "style": "primary",
                "action_id": "reminder_done",
                "value": str(reminder_id),
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "⏰ Snooze 15m", "emoji": True},
                "action_id": "reminder_snooze",
                "value": str(reminder_id),
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "❌ Cancel", "emoji": True},
                "style": "danger",
                "action_id": "reminder_cancel",
                "value": str(reminder_id),
            },
        ]
    })

    return {
        "text": fallback_text,
        "blocks": blocks,
    }


def format_confirmation_message(reminder: dict) -> dict:
    """Format an ephemeral confirmation message after creating a reminder."""
    priority = reminder.get("priority", "medium")
    emoji = PRIORITY_EMOJI.get(priority, "🔵")
    task_text = reminder.get("task_text", "")
    remind_at = reminder.get("remind_at", "unknown")
    target = reminder.get("target_user_id", "unknown")

    text = (
        f"✅ Reminder scheduled!\n\n"
        f"{emoji} *{task_text}*\n"
        f"👤 For: <@{target}>\n"
        f"⏰ At: {remind_at}\n"
    )

    if reminder.get("repeat"):
        text += f"🔁 Repeat: {reminder['repeat']}\n"

    return {
        "text": text,
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": text,
                }
            }
        ]
    }


def format_action_response(action: str, reminder: dict) -> dict:
    """Format a response message after a button action."""
    task_text = reminder.get("task_text", "")

    messages = {
        "reminder_done": f"✅ Marked as completed: *{task_text}*\nGreat job! 🎉",
        "reminder_snooze": f"⏰ Snoozed for 15 minutes: *{task_text}*\nI'll remind you again soon.",
        "reminder_cancel": f"❌ Cancelled: *{task_text}*",
    }

    text = messages.get(action, f"Action '{action}' processed for: {task_text}")

    return {
        "text": text,
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": text,
                }
            }
        ]
    }
