"""DynamoDB client wrapper for single-table design."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import boto3
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError

from .exceptions import NotFoundError

logger = Logger(child=True)


def convert_floats_to_decimal(obj: Any) -> Any:
    """Recursively convert floats to Decimal for DynamoDB compatibility.

    DynamoDB does not support Python float types. This function converts
    all floats in nested dicts/lists to Decimal.

    Args:
        obj: Any Python object (dict, list, or primitive)

    Returns:
        The object with all floats converted to Decimal
    """
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    return obj


class DynamoDBClient:
    """DynamoDB client wrapper with consistent error handling and logging.

    Implements single-table design patterns with PK/SK composite keys.
    """

    def __init__(self, table_name: str) -> None:
        """Initialize with table name.

        Args:
            table_name: Name of the DynamoDB table
        """
        self.table_name = table_name
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)

    def put_item(self, pk: str, sk: str, data: dict[str, Any]) -> dict[str, Any]:
        """Put an item into the table.

        Args:
            pk: Partition key value
            sk: Sort key value
            data: Additional attributes to store

        Returns:
            The complete item that was stored
        """
        now = datetime.now(UTC).isoformat()
        item = {
            "PK": pk,
            "SK": sk,
            **data,
            "updated_at": now,
        }

        # Set created_at only if not provided
        if "created_at" not in item:
            item["created_at"] = now

        try:
            self.table.put_item(Item=item)
            logger.info("Item created", extra={"pk": pk, "sk": sk})
            return item
        except ClientError as e:
            logger.error("Failed to put item", extra={"error": str(e), "pk": pk, "sk": sk})
            raise

    def get_item(self, pk: str, sk: str) -> dict[str, Any] | None:
        """Get a single item by PK and SK.

        Args:
            pk: Partition key value
            sk: Sort key value

        Returns:
            Item dict or None if not found
        """
        try:
            response = self.table.get_item(Key={"PK": pk, "SK": sk})
            item = response.get("Item")
            if item:
                logger.debug("Item found", extra={"pk": pk, "sk": sk})
            return item
        except ClientError as e:
            logger.error("Failed to get item", extra={"error": str(e), "pk": pk, "sk": sk})
            raise

    def query_by_pk(
        self,
        pk: str,
        sk_prefix: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query items by partition key with optional SK prefix.

        Args:
            pk: Partition key value
            sk_prefix: Optional sort key prefix filter
            limit: Maximum items to return

        Returns:
            List of matching items
        """
        try:
            params: dict[str, Any] = {
                "KeyConditionExpression": "PK = :pk",
                "ExpressionAttributeValues": {":pk": pk},
                "Limit": limit,
            }

            if sk_prefix:
                params["KeyConditionExpression"] += " AND begins_with(SK, :sk)"
                params["ExpressionAttributeValues"][":sk"] = sk_prefix

            response = self.table.query(**params)
            items = response.get("Items", [])
            logger.debug("Query complete", extra={"pk": pk, "count": len(items)})
            return items
        except ClientError as e:
            logger.error("Failed to query", extra={"error": str(e), "pk": pk})
            raise

    def delete_item(self, pk: str, sk: str) -> bool:
        """Delete an item by PK and SK.

        Args:
            pk: Partition key value
            sk: Sort key value

        Returns:
            True if deleted, False if not found
        """
        try:
            self.table.delete_item(
                Key={"PK": pk, "SK": sk},
                ConditionExpression="attribute_exists(PK)",
            )
            logger.info("Item deleted", extra={"pk": pk, "sk": sk})
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                logger.warning("Item not found for delete", extra={"pk": pk, "sk": sk})
                return False
            logger.error("Failed to delete", extra={"error": str(e), "pk": pk, "sk": sk})
            raise

    def update_item(
        self,
        pk: str,
        sk: str,
        updates: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Update specific attributes of an item.

        Args:
            pk: Partition key value
            sk: Sort key value
            updates: Dict of attribute names to new values

        Returns:
            Updated item or None if not found
        """
        if not updates:
            return self.get_item(pk, sk)

        # Build update expression
        update_parts = []
        names: dict[str, str] = {}
        values: dict[str, Any] = {":updated_at": datetime.now(UTC).isoformat()}

        for i, (key, value) in enumerate(updates.items()):
            placeholder = f"#attr{i}"
            value_placeholder = f":val{i}"
            update_parts.append(f"{placeholder} = {value_placeholder}")
            names[placeholder] = key
            values[value_placeholder] = value

        update_parts.append("updated_at = :updated_at")
        update_expr = "SET " + ", ".join(update_parts)

        try:
            response = self.table.update_item(
                Key={"PK": pk, "SK": sk},
                UpdateExpression=update_expr,
                ExpressionAttributeNames=names,
                ExpressionAttributeValues=values,
                ReturnValues="ALL_NEW",
                ConditionExpression="attribute_exists(PK)",
            )
            logger.info("Item updated", extra={"pk": pk, "sk": sk})
            return response.get("Attributes")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                logger.warning("Item not found for update", extra={"pk": pk, "sk": sk})
                return None
            logger.error("Failed to update", extra={"error": str(e), "pk": pk, "sk": sk})
            raise

    def get_item_or_raise(
        self,
        pk: str,
        sk: str,
        resource_type: str,
        resource_id: str,
    ) -> dict[str, Any]:
        """Get an item or raise NotFoundError if it doesn't exist.

        Args:
            pk: Partition key value
            sk: Sort key value
            resource_type: Type of resource for error message
            resource_id: ID of resource for error message

        Returns:
            The item dict

        Raises:
            NotFoundError: If item doesn't exist
        """
        item = self.get_item(pk, sk)
        if item is None:
            raise NotFoundError(resource_type, resource_id)
        return item
