"""
Tests for the Slack Block Kit message formatter.
"""
import pytest
from src.core.slack_formatter import (
    format_reminder_message,
    format_confirmation_message,
    format_action_response,
)


class TestFormatReminderMessage:
    """Test format_reminder_message function."""

    def test_basic_message(self, sample_reminder):
        result = format_reminder_message(sample_reminder)
        assert "text" in result
        assert "blocks" in result
        assert "Reminder" in result["text"]
        assert "Complete the quarterly report" in result["text"]

    def test_contains_action_buttons(self, sample_reminder):
        result = format_reminder_message(sample_reminder)
        blocks = result["blocks"]
        action_block = [b for b in blocks if b.get("type") == "actions"]
        assert len(action_block) == 1
        elements = action_block[0]["elements"]
        action_ids = [e["action_id"] for e in elements]
        assert "reminder_done" in action_ids
        assert "reminder_snooze" in action_ids
        assert "reminder_cancel" in action_ids

    def test_priority_emoji(self, sample_reminder):
        sample_reminder["priority"] = "urgent"
        result = format_reminder_message(sample_reminder)
        assert "🔴" in result["text"]

    def test_with_context_summary(self, sample_reminder):
        result = format_reminder_message(
            sample_reminder,
            context_summary="✅ Completed 5/10 tasks (50.0% rate)",
        )
        blocks = result["blocks"]
        all_text = str(blocks)
        assert "50.0%" in all_text

    def test_with_related_tasks(self, sample_reminder):
        related = [
            {"task_text": "Review budget", "priority": "medium"},
            {"task_text": "Update slides", "priority": "low"},
        ]
        result = format_reminder_message(
            sample_reminder,
            related_tasks=related,
        )
        all_text = str(result["blocks"])
        assert "Review budget" in all_text

    def test_project_shown_in_blocks(self, sample_reminder):
        result = format_reminder_message(sample_reminder)
        all_text = str(result["blocks"])
        assert "Finance" in all_text


class TestFormatConfirmationMessage:
    """Test format_confirmation_message function."""

    def test_basic_confirmation(self, sample_reminder):
        result = format_confirmation_message(sample_reminder)
        assert "Reminder scheduled" in result["text"]
        assert "Complete the quarterly report" in result["text"]

    def test_shows_repeat(self, sample_reminder):
        sample_reminder["repeat"] = "weekly"
        result = format_confirmation_message(sample_reminder)
        assert "weekly" in result["text"]


class TestFormatActionResponse:
    """Test format_action_response function."""

    def test_done_action(self, sample_reminder):
        result = format_action_response("reminder_done", sample_reminder)
        assert "completed" in result["text"].lower() or "✅" in result["text"]

    def test_snooze_action(self, sample_reminder):
        result = format_action_response("reminder_snooze", sample_reminder)
        assert "Snoozed" in result["text"] or "⏰" in result["text"]

    def test_cancel_action(self, sample_reminder):
        result = format_action_response("reminder_cancel", sample_reminder)
        assert "Cancelled" in result["text"] or "❌" in result["text"]

    def test_unknown_action(self, sample_reminder):
        result = format_action_response("unknown_action", sample_reminder)
        assert "text" in result
