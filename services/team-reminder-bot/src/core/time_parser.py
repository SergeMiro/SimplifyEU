"""
Natural language time parser for reminder scheduling.

Supports formats:
- ISO datetime: "2026-02-17T14:00:00"
- Relative: "in 2 hours", "in 30 minutes", "через 2 часа"
- Named: "tomorrow 9:00", "завтра 9:00", "next monday 10:00"
- Date-based: "15.02.2026 14:00", "02/15/2026 14:00"
"""
import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import dateparser

logger = logging.getLogger(__name__)

# Relative time patterns (English + Russian)
RELATIVE_PATTERNS = [
    # English
    (r"in\s+(\d+)\s*min(?:ute)?s?", "minutes"),
    (r"in\s+(\d+)\s*hours?", "hours"),
    (r"in\s+(\d+)\s*days?", "days"),
    (r"in\s+(\d+)\s*weeks?", "weeks"),
    # Russian
    (r"через\s+(\d+)\s*мин(?:ут[аыу]?)?", "minutes"),
    (r"через\s+(\d+)\s*час(?:а|ов)?", "hours"),
    (r"через\s+(\d+)\s*дн(?:ей|я)?", "days"),
    (r"через\s+(\d+)\s*недел[юиь]", "weeks"),
]


def parse_time(text: str, base_time: Optional[datetime] = None) -> Optional[datetime]:
    """
    Parse a natural-language time expression into a datetime object.

    Args:
        text: The time expression to parse.
        base_time: Reference time for relative expressions (defaults to now UTC).

    Returns:
        Parsed datetime in UTC, or None if parsing failed.
    """
    if not text or not text.strip():
        return None

    text = text.strip()
    now = base_time or datetime.now(timezone.utc)

    # 1. Try relative patterns first (most common)
    result = _parse_relative(text, now)
    if result:
        logger.debug(f"Parsed relative time: '{text}' -> {result}")
        return result

    # 2. Try dateparser for natural language
    result = _parse_natural(text, now)
    if result:
        logger.debug(f"Parsed natural time: '{text}' -> {result}")
        return result

    logger.warning(f"Failed to parse time expression: '{text}'")
    return None


def _parse_relative(text: str, now: datetime) -> Optional[datetime]:
    """Parse relative time expressions like 'in 30 minutes' or 'через 2 часа'."""
    text_lower = text.lower().strip()

    for pattern, unit in RELATIVE_PATTERNS:
        match = re.match(pattern, text_lower, re.IGNORECASE)
        if match:
            value = int(match.group(1))
            if value <= 0:
                return None
            # Safety limit: max 365 days
            if unit == "weeks" and value > 52:
                return None
            if unit == "days" and value > 365:
                return None
            if unit == "hours" and value > 8760:
                return None
            if unit == "minutes" and value > 525600:
                return None

            delta = timedelta(**{unit: value})
            return now + delta

    return None


def _parse_natural(text: str, now: datetime) -> Optional[datetime]:
    """Parse natural language time using dateparser library."""
    settings = {
        "PREFER_DATES_FROM": "future",
        "RELATIVE_BASE": now.replace(tzinfo=None),
        "RETURN_AS_TIMEZONE_AWARE": False,
        "PARSERS": ["relative-time", "absolute-time", "timestamp", "custom-formats"],
    }

    parsed = dateparser.parse(text, settings=settings, languages=["en", "ru", "fr", "es"])

    if parsed:
        # Ensure it's in the future
        parsed_utc = parsed.replace(tzinfo=timezone.utc)
        if parsed_utc <= now:
            # If the parsed time is in the past, try adding a day
            parsed_utc += timedelta(days=1)
        return parsed_utc

    return None


def calculate_delay_seconds(remind_at: datetime, now: Optional[datetime] = None) -> int:
    """Calculate delay in seconds from now to the reminder time."""
    now = now or datetime.now(timezone.utc)

    if remind_at.tzinfo is None:
        remind_at = remind_at.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    delta = (remind_at - now).total_seconds()
    return max(0, int(delta))


def format_relative_time(dt: datetime, now: Optional[datetime] = None) -> str:
    """Format a datetime as a human-readable relative time string."""
    now = now or datetime.now(timezone.utc)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    diff = dt - now
    total_seconds = diff.total_seconds()

    if total_seconds < 0:
        return "overdue"
    elif total_seconds < 60:
        return "less than a minute"
    elif total_seconds < 3600:
        mins = int(total_seconds // 60)
        return f"in {mins} minute{'s' if mins > 1 else ''}"
    elif total_seconds < 86400:
        hours = int(total_seconds // 3600)
        return f"in {hours} hour{'s' if hours > 1 else ''}"
    else:
        days = int(total_seconds // 86400)
        return f"in {days} day{'s' if days > 1 else ''}"
