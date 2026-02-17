"""
Tests for the natural language time parser.
"""
import pytest
from datetime import datetime, timezone, timedelta
from src.core.time_parser import parse_time, calculate_delay_seconds, format_relative_time


class TestParseTime:
    """Test parse_time function."""

    def setup_method(self):
        self.now = datetime(2026, 2, 17, 12, 0, 0, tzinfo=timezone.utc)

    # -- Relative time (English) --

    def test_in_30_minutes(self):
        result = parse_time("in 30 minutes", self.now)
        assert result is not None
        expected = self.now + timedelta(minutes=30)
        assert abs((result - expected).total_seconds()) < 2

    def test_in_2_hours(self):
        result = parse_time("in 2 hours", self.now)
        assert result is not None
        expected = self.now + timedelta(hours=2)
        assert abs((result - expected).total_seconds()) < 2

    def test_in_3_days(self):
        result = parse_time("in 3 days", self.now)
        assert result is not None
        expected = self.now + timedelta(days=3)
        assert abs((result - expected).total_seconds()) < 2

    def test_in_1_week(self):
        result = parse_time("in 1 week", self.now)
        assert result is not None
        expected = self.now + timedelta(weeks=1)
        assert abs((result - expected).total_seconds()) < 2

    # -- Relative time (Russian) --

    def test_cherez_2_chasa(self):
        result = parse_time("через 2 часа", self.now)
        assert result is not None
        expected = self.now + timedelta(hours=2)
        assert abs((result - expected).total_seconds()) < 2

    def test_cherez_30_minut(self):
        result = parse_time("через 30 минут", self.now)
        assert result is not None
        expected = self.now + timedelta(minutes=30)
        assert abs((result - expected).total_seconds()) < 2

    def test_cherez_5_dney(self):
        result = parse_time("через 5 дней", self.now)
        assert result is not None
        expected = self.now + timedelta(days=5)
        assert abs((result - expected).total_seconds()) < 2

    # -- Edge cases --

    def test_empty_string(self):
        result = parse_time("", self.now)
        assert result is None

    def test_none_input(self):
        result = parse_time(None, self.now)
        assert result is None

    def test_invalid_string(self):
        result = parse_time("not a time at all xyzzy", self.now)
        assert result is None

    def test_zero_minutes(self):
        result = parse_time("in 0 minutes", self.now)
        assert result is None

    def test_result_is_utc(self):
        result = parse_time("in 1 hour", self.now)
        assert result is not None
        assert result.tzinfo is not None


class TestCalculateDelaySeconds:
    """Test calculate_delay_seconds function."""

    def test_future_time(self):
        now = datetime(2026, 2, 17, 12, 0, 0, tzinfo=timezone.utc)
        future = now + timedelta(hours=1)
        delay = calculate_delay_seconds(future, now)
        assert delay == 3600

    def test_past_time_returns_zero(self):
        now = datetime(2026, 2, 17, 12, 0, 0, tzinfo=timezone.utc)
        past = now - timedelta(hours=1)
        delay = calculate_delay_seconds(past, now)
        assert delay == 0

    def test_same_time_returns_zero(self):
        now = datetime(2026, 2, 17, 12, 0, 0, tzinfo=timezone.utc)
        delay = calculate_delay_seconds(now, now)
        assert delay == 0


class TestFormatRelativeTime:
    """Test format_relative_time function."""

    def test_less_than_minute(self):
        now = datetime(2026, 2, 17, 12, 0, 0, tzinfo=timezone.utc)
        dt = now + timedelta(seconds=30)
        assert format_relative_time(dt, now) == "less than a minute"

    def test_minutes(self):
        now = datetime(2026, 2, 17, 12, 0, 0, tzinfo=timezone.utc)
        dt = now + timedelta(minutes=5)
        assert format_relative_time(dt, now) == "in 5 minutes"

    def test_hours(self):
        now = datetime(2026, 2, 17, 12, 0, 0, tzinfo=timezone.utc)
        dt = now + timedelta(hours=3)
        assert format_relative_time(dt, now) == "in 3 hours"

    def test_days(self):
        now = datetime(2026, 2, 17, 12, 0, 0, tzinfo=timezone.utc)
        dt = now + timedelta(days=2)
        assert format_relative_time(dt, now) == "in 2 days"

    def test_overdue(self):
        now = datetime(2026, 2, 17, 12, 0, 0, tzinfo=timezone.utc)
        dt = now - timedelta(hours=1)
        assert format_relative_time(dt, now) == "overdue"
