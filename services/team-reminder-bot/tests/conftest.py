import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from datetime import datetime, timezone, timedelta


@pytest.fixture
def sample_reminder():
    """Sample reminder record."""
    now = datetime.now(timezone.utc)
    return {
        "id": "test-reminder-001",
        "team_id": "test-team-001",
        "creator_user_id": "U_CREATOR",
        "target_user_id": "U_TARGET",
        "task_text": "Complete the quarterly report",
        "context": "Q4 2025 financial report for the board meeting",
        "project": "Finance",
        "priority": "high",
        "remind_at": (now + timedelta(hours=2)).isoformat(),
        "status": "pending",
        "repeat": None,
        "parent_reminder_id": None,
        "snooze_count": 0,
        "retry_count": 0,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }


@pytest.fixture
def sample_reminders():
    """List of sample reminders with different statuses."""
    now = datetime.now(timezone.utc)
    return [
        {
            "id": f"test-reminder-{i:03d}",
            "team_id": "test-team-001",
            "creator_user_id": "U_CREATOR",
            "target_user_id": "U_TARGET",
            "task_text": f"Task #{i}",
            "priority": ["low", "medium", "high", "urgent"][i % 4],
            "remind_at": (now + timedelta(hours=i)).isoformat(),
            "status": ["pending", "sent", "completed", "cancelled"][i % 4],
            "snooze_count": 0,
            "retry_count": 0,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        for i in range(8)
    ]
