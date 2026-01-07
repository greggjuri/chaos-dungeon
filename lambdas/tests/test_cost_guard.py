"""Tests for cost guard module."""

from unittest.mock import MagicMock

from shared.cost_guard import CostGuard, LimitStatus, get_limit_message


class TestCostGuard:
    """Tests for CostGuard."""

    def test_allows_request_under_limit(self):
        """Request allowed when under all limits."""
        mock_tracker = MagicMock()
        mock_tracker.get_global_usage.return_value = {
            "input_tokens": 1000,
            "output_tokens": 500,
            "request_count": 5,
        }
        mock_tracker.get_session_usage.return_value = {
            "input_tokens": 100,
            "output_tokens": 50,
            "request_count": 1,
        }

        guard = CostGuard(mock_tracker)
        status = guard.check_limits("test-session")

        assert status.allowed is True
        assert status.reason is None
        assert status.global_usage == 1500
        assert status.session_usage == 150

    def test_blocks_at_global_limit(self):
        """Request blocked when global limit reached."""
        mock_tracker = MagicMock()
        mock_tracker.get_global_usage.return_value = {
            "input_tokens": 300000,
            "output_tokens": 200000,
            "request_count": 1000,
        }
        mock_tracker.get_session_usage.return_value = {
            "input_tokens": 100,
            "output_tokens": 50,
            "request_count": 1,
        }

        guard = CostGuard(mock_tracker)
        status = guard.check_limits("test-session")

        assert status.allowed is False
        assert status.reason == "global_limit"
        assert status.global_remaining == 0

    def test_blocks_at_session_limit(self):
        """Request blocked when session limit reached."""
        mock_tracker = MagicMock()
        mock_tracker.get_global_usage.return_value = {
            "input_tokens": 1000,
            "output_tokens": 500,
            "request_count": 5,
        }
        mock_tracker.get_session_usage.return_value = {
            "input_tokens": 30000,
            "output_tokens": 20000,
            "request_count": 100,
        }

        guard = CostGuard(mock_tracker)
        status = guard.check_limits("test-session")

        assert status.allowed is False
        assert status.reason == "session_limit"
        assert status.session_remaining == 0

    def test_global_limit_takes_priority(self):
        """Global limit checked before session limit."""
        mock_tracker = MagicMock()
        # Both limits exceeded
        mock_tracker.get_global_usage.return_value = {
            "input_tokens": 500000,
            "output_tokens": 100000,
            "request_count": 1000,
        }
        mock_tracker.get_session_usage.return_value = {
            "input_tokens": 50000,
            "output_tokens": 10000,
            "request_count": 100,
        }

        guard = CostGuard(mock_tracker)
        status = guard.check_limits("test-session")

        assert status.allowed is False
        assert status.reason == "global_limit"

    def test_limit_status_remaining_calculated(self):
        """LimitStatus calculates remaining tokens correctly."""
        mock_tracker = MagicMock()
        mock_tracker.get_global_usage.return_value = {
            "input_tokens": 100000,
            "output_tokens": 50000,
            "request_count": 500,
        }
        mock_tracker.get_session_usage.return_value = {
            "input_tokens": 10000,
            "output_tokens": 5000,
            "request_count": 50,
        }

        guard = CostGuard(mock_tracker)
        status = guard.check_limits("test-session")

        assert status.allowed is True
        assert status.global_remaining == 500_000 - 150_000  # 350K remaining
        assert status.session_remaining == 50_000 - 15_000  # 35K remaining


class TestGetLimitMessage:
    """Tests for get_limit_message."""

    def test_global_limit_message(self):
        """Global limit message is narrative."""
        msg = get_limit_message("global_limit")
        assert "dungeon grows silent" in msg.lower()
        assert "midnight UTC" in msg

    def test_session_limit_message(self):
        """Session limit message is narrative."""
        msg = get_limit_message("session_limit")
        assert "fatigue" in msg.lower()
        assert "session limit" in msg.lower()

    def test_unknown_reason_message(self):
        """Unknown reason returns generic message."""
        msg = get_limit_message("unknown")
        assert "temporarily unavailable" in msg.lower()

    def test_empty_reason_message(self):
        """Empty reason returns generic message."""
        msg = get_limit_message("")
        assert "temporarily unavailable" in msg.lower()


class TestLimitStatus:
    """Tests for LimitStatus dataclass."""

    def test_default_values(self):
        """LimitStatus has correct defaults."""
        status = LimitStatus(allowed=True)
        assert status.allowed is True
        assert status.reason is None
        assert status.global_usage == 0
        assert status.session_usage == 0
        assert status.global_remaining == 0
        assert status.session_remaining == 0

    def test_all_fields(self):
        """LimitStatus stores all fields."""
        status = LimitStatus(
            allowed=False,
            reason="global_limit",
            global_usage=500000,
            session_usage=10000,
            global_remaining=0,
            session_remaining=40000,
        )
        assert status.allowed is False
        assert status.reason == "global_limit"
        assert status.global_usage == 500000
        assert status.session_usage == 10000
        assert status.global_remaining == 0
        assert status.session_remaining == 40000
