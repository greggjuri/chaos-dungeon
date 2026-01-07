"""Tests for token tracker module."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from shared.token_tracker import TokenTracker, get_today_key, get_ttl_epoch


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_today_key_format(self):
        """Today key has correct format."""
        key = get_today_key()
        # Should be YYYY-MM-DD format
        assert len(key) == 10
        assert key[4] == "-"
        assert key[7] == "-"

    def test_get_ttl_epoch_future(self):
        """TTL epoch is in the future."""
        import time

        now = int(time.time())
        ttl = get_ttl_epoch(days=7)
        # Should be ~7 days in the future (allow 1 day tolerance)
        assert ttl > now + (6 * 24 * 60 * 60)
        assert ttl < now + (8 * 24 * 60 * 60)

    def test_get_ttl_epoch_90_days(self):
        """TTL for 90 days is correct."""
        import time

        now = int(time.time())
        ttl = get_ttl_epoch(days=90)
        # Should be ~90 days in the future
        assert ttl > now + (89 * 24 * 60 * 60)
        assert ttl < now + (91 * 24 * 60 * 60)


class TestTokenTracker:
    """Tests for TokenTracker."""

    @pytest.fixture
    def mock_table(self):
        """Create a mock DynamoDB table."""
        return MagicMock()

    @pytest.fixture
    def tracker(self, mock_table):
        """Create a TokenTracker with mocked table."""
        with patch("boto3.resource") as mock_resource:
            mock_dynamodb = MagicMock()
            mock_resource.return_value = mock_dynamodb
            mock_dynamodb.Table.return_value = mock_table

            tracker = TokenTracker(table_name="test-table")
            return tracker

    def test_get_global_usage_empty(self, tracker, mock_table):
        """Get global usage returns zeros when no data."""
        mock_table.get_item.return_value = {}

        result = tracker.get_global_usage()

        assert result == {
            "input_tokens": 0,
            "output_tokens": 0,
            "request_count": 0,
        }

    def test_get_global_usage_with_data(self, tracker, mock_table):
        """Get global usage returns correct values."""
        mock_table.get_item.return_value = {
            "Item": {
                "input_tokens": Decimal("1000"),
                "output_tokens": Decimal("500"),
                "request_count": Decimal("10"),
            }
        }

        result = tracker.get_global_usage()

        assert result == {
            "input_tokens": 1000,
            "output_tokens": 500,
            "request_count": 10,
        }

    def test_get_session_usage_empty(self, tracker, mock_table):
        """Get session usage returns zeros when no data."""
        mock_table.get_item.return_value = {}

        result = tracker.get_session_usage("test-session")

        assert result == {
            "input_tokens": 0,
            "output_tokens": 0,
            "request_count": 0,
        }

    def test_get_session_usage_with_data(self, tracker, mock_table):
        """Get session usage returns correct values."""
        mock_table.get_item.return_value = {
            "Item": {
                "input_tokens": Decimal("500"),
                "output_tokens": Decimal("200"),
                "request_count": Decimal("5"),
            }
        }

        result = tracker.get_session_usage("test-session")

        assert result == {
            "input_tokens": 500,
            "output_tokens": 200,
            "request_count": 5,
        }

    def test_increment_usage_updates_both_counters(self, tracker, mock_table):
        """Increment usage updates global and session counters."""
        mock_table.update_item.return_value = {
            "Attributes": {
                "input_tokens": Decimal("100"),
                "output_tokens": Decimal("50"),
                "request_count": Decimal("1"),
            }
        }

        global_usage, session_usage = tracker.increment_usage(
            session_id="test-session",
            input_tokens=100,
            output_tokens=50,
        )

        # Should call update_item twice (global + session)
        assert mock_table.update_item.call_count == 2

        # Check global update call
        global_call = mock_table.update_item.call_args_list[0]
        assert global_call[1]["Key"]["PK"] == "USAGE#GLOBAL"
        assert "DATE#" in global_call[1]["Key"]["SK"]

        # Check session update call
        session_call = mock_table.update_item.call_args_list[1]
        assert session_call[1]["Key"]["PK"] == "SESSION#test-session"
        assert "USAGE#DATE#" in session_call[1]["Key"]["SK"]

    def test_increment_usage_returns_new_values(self, tracker, mock_table):
        """Increment usage returns updated totals."""
        # First call returns global values
        # Second call returns session values
        mock_table.update_item.side_effect = [
            {
                "Attributes": {
                    "input_tokens": Decimal("1000"),
                    "output_tokens": Decimal("500"),
                    "request_count": Decimal("10"),
                }
            },
            {
                "Attributes": {
                    "input_tokens": Decimal("100"),
                    "output_tokens": Decimal("50"),
                    "request_count": Decimal("1"),
                }
            },
        ]

        global_usage, session_usage = tracker.increment_usage(
            session_id="test-session",
            input_tokens=100,
            output_tokens=50,
        )

        assert global_usage == {
            "input_tokens": 1000,
            "output_tokens": 500,
            "request_count": 10,
        }
        assert session_usage == {
            "input_tokens": 100,
            "output_tokens": 50,
            "request_count": 1,
        }

    def test_get_global_usage_with_custom_date(self, tracker, mock_table):
        """Can query specific date for global usage."""
        mock_table.get_item.return_value = {}

        tracker.get_global_usage(date_key="2026-01-01")

        # Check the SK includes the custom date
        call_args = mock_table.get_item.call_args[1]
        assert call_args["Key"]["SK"] == "DATE#2026-01-01"

    def test_get_session_usage_with_custom_date(self, tracker, mock_table):
        """Can query specific date for session usage."""
        mock_table.get_item.return_value = {}

        tracker.get_session_usage("test-session", date_key="2026-01-01")

        # Check the SK includes the custom date
        call_args = mock_table.get_item.call_args[1]
        assert call_args["Key"]["SK"] == "USAGE#DATE#2026-01-01"
