"""Token usage tracking for cost protection."""

import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import boto3
from aws_lambda_powertools import Logger, Metrics
from aws_lambda_powertools.metrics import MetricUnit

logger = Logger(child=True)
metrics = Metrics(namespace="ChaosDungeon")


def get_today_key() -> str:
    """Get today's date key in UTC."""
    return datetime.now(UTC).strftime("%Y-%m-%d")


def get_ttl_epoch(days: int) -> int:
    """Get TTL epoch timestamp for auto-deletion."""
    future = datetime.now(UTC) + timedelta(days=days)
    return int(future.timestamp())


class TokenTracker:
    """Tracks token usage in DynamoDB."""

    def __init__(self, table_name: str | None = None):
        """Initialize tracker with table name.

        Args:
            table_name: DynamoDB table name. Defaults to TABLE_NAME env var.
        """
        self.table_name = table_name or os.environ.get("TABLE_NAME", "")
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(self.table_name)

    def get_global_usage(self, date_key: str | None = None) -> dict:
        """Get global token usage for a date.

        Args:
            date_key: Date in YYYY-MM-DD format. Defaults to today.

        Returns:
            Dict with input_tokens, output_tokens, request_count
        """
        date_key = date_key or get_today_key()

        response = self.table.get_item(
            Key={"PK": "USAGE#GLOBAL", "SK": f"DATE#{date_key}"}
        )

        item = response.get("Item", {})
        return {
            "input_tokens": int(item.get("input_tokens", 0)),
            "output_tokens": int(item.get("output_tokens", 0)),
            "request_count": int(item.get("request_count", 0)),
        }

    def get_session_usage(
        self, session_id: str, date_key: str | None = None
    ) -> dict:
        """Get session token usage for a date.

        Args:
            session_id: Session UUID
            date_key: Date in YYYY-MM-DD format. Defaults to today.

        Returns:
            Dict with input_tokens, output_tokens, request_count
        """
        date_key = date_key or get_today_key()

        response = self.table.get_item(
            Key={
                "PK": f"SESSION#{session_id}",
                "SK": f"USAGE#DATE#{date_key}",
            }
        )

        item = response.get("Item", {})
        return {
            "input_tokens": int(item.get("input_tokens", 0)),
            "output_tokens": int(item.get("output_tokens", 0)),
            "request_count": int(item.get("request_count", 0)),
        }

    def increment_usage(
        self,
        session_id: str,
        input_tokens: int,
        output_tokens: int,
    ) -> tuple[dict, dict]:
        """Increment both global and session usage atomically.

        Args:
            session_id: Current session ID
            input_tokens: Input tokens consumed
            output_tokens: Output tokens consumed

        Returns:
            Tuple of (global_usage, session_usage) after increment
        """
        date_key = get_today_key()
        now = datetime.now(UTC).isoformat()

        # Update global counter
        global_response = self.table.update_item(
            Key={"PK": "USAGE#GLOBAL", "SK": f"DATE#{date_key}"},
            UpdateExpression="""
                SET input_tokens = if_not_exists(input_tokens, :zero) + :input,
                    output_tokens = if_not_exists(output_tokens, :zero) + :output,
                    request_count = if_not_exists(request_count, :zero) + :one,
                    updated_at = :now,
                    #ttl_attr = :ttl
            """,
            ExpressionAttributeNames={"#ttl_attr": "ttl"},
            ExpressionAttributeValues={
                ":input": Decimal(str(input_tokens)),
                ":output": Decimal(str(output_tokens)),
                ":zero": Decimal("0"),
                ":one": Decimal("1"),
                ":now": now,
                ":ttl": get_ttl_epoch(days=90),
            },
            ReturnValues="ALL_NEW",
        )

        # Update session counter
        session_response = self.table.update_item(
            Key={
                "PK": f"SESSION#{session_id}",
                "SK": f"USAGE#DATE#{date_key}",
            },
            UpdateExpression="""
                SET input_tokens = if_not_exists(input_tokens, :zero) + :input,
                    output_tokens = if_not_exists(output_tokens, :zero) + :output,
                    request_count = if_not_exists(request_count, :zero) + :one,
                    updated_at = :now,
                    #ttl_attr = :ttl
            """,
            ExpressionAttributeNames={"#ttl_attr": "ttl"},
            ExpressionAttributeValues={
                ":input": Decimal(str(input_tokens)),
                ":output": Decimal(str(output_tokens)),
                ":zero": Decimal("0"),
                ":one": Decimal("1"),
                ":now": now,
                ":ttl": get_ttl_epoch(days=7),
            },
            ReturnValues="ALL_NEW",
        )

        global_item = global_response["Attributes"]
        session_item = session_response["Attributes"]

        logger.info(
            "Token usage recorded",
            extra={
                "session_id": session_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "global_total": int(global_item["input_tokens"])
                + int(global_item["output_tokens"]),
                "session_total": int(session_item["input_tokens"])
                + int(session_item["output_tokens"]),
            },
        )

        # Emit CloudWatch metric for token consumption
        metrics.add_metric(
            name="TokensConsumed",
            unit=MetricUnit.Count,
            value=input_tokens + output_tokens,
        )

        return (
            {
                "input_tokens": int(global_item["input_tokens"]),
                "output_tokens": int(global_item["output_tokens"]),
                "request_count": int(global_item["request_count"]),
            },
            {
                "input_tokens": int(session_item["input_tokens"]),
                "output_tokens": int(session_item["output_tokens"]),
                "request_count": int(session_item["request_count"]),
            },
        )
