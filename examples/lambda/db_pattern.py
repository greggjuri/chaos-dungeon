"""
Example DynamoDB access patterns for Chaos Dungeon.

This demonstrates:
- Single-table design with PK/SK patterns
- Pydantic models for data validation
- Common CRUD operations
- Error handling
"""
from datetime import datetime, timezone
from typing import TypeVar
from uuid import uuid4

import boto3
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError
from pydantic import BaseModel, Field

logger = Logger()

# Type variable for generic operations
T = TypeVar("T", bound=BaseModel)


class DynamoDBClient:
    """
    DynamoDB client wrapper for single-table design.

    Handles all database operations with consistent error handling
    and logging.
    """

    def __init__(self, table_name: str) -> None:
        """Initialize with table name."""
        self.table_name = table_name
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)

    def put_item(self, pk: str, sk: str, data: dict) -> dict:
        """
        Put an item into the table.

        Args:
            pk: Partition key value
            sk: Sort key value
            data: Additional attributes

        Returns:
            The complete item that was stored
        """
        item = {
            "PK": pk,
            "SK": sk,
            **data,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            self.table.put_item(Item=item)
            logger.info("Item created", extra={"pk": pk, "sk": sk})
            return item
        except ClientError as e:
            logger.error("Failed to put item", extra={"error": str(e)})
            raise

    def get_item(self, pk: str, sk: str) -> dict | None:
        """
        Get a single item by PK and SK.

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
            logger.error("Failed to get item", extra={"error": str(e)})
            raise

    def query_by_pk(
        self,
        pk: str,
        sk_prefix: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        Query items by partition key with optional SK prefix.

        Args:
            pk: Partition key value
            sk_prefix: Optional sort key prefix filter
            limit: Maximum items to return

        Returns:
            List of matching items
        """
        try:
            params = {
                "KeyConditionExpression": "PK = :pk",
                "ExpressionAttributeValues": {":pk": pk},
                "Limit": limit,
            }

            if sk_prefix:
                params["KeyConditionExpression"] += " AND begins_with(SK, :sk)"
                params["ExpressionAttributeValues"][":sk"] = sk_prefix

            response = self.table.query(**params)
            items = response.get("Items", [])
            logger.debug(
                "Query complete",
                extra={"pk": pk, "count": len(items)},
            )
            return items
        except ClientError as e:
            logger.error("Failed to query", extra={"error": str(e)})
            raise

    def delete_item(self, pk: str, sk: str) -> bool:
        """
        Delete an item by PK and SK.

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
            logger.error("Failed to delete", extra={"error": str(e)})
            raise

    def update_item(
        self,
        pk: str,
        sk: str,
        updates: dict,
    ) -> dict | None:
        """
        Update specific attributes of an item.

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
        names = {}
        values = {":updated_at": datetime.now(timezone.utc).isoformat()}

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
            logger.error("Failed to update", extra={"error": str(e)})
            raise


# Example usage with Pydantic models
class Character(BaseModel):
    """Character model for database storage."""

    character_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    name: str = Field(..., min_length=1, max_length=50)
    character_class: str
    level: int = Field(default=1, ge=1, le=36)
    hp: int = Field(default=1, ge=0)
    max_hp: int = Field(default=1, ge=1)
    gold: int = Field(default=0, ge=0)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_db_item(self) -> tuple[str, str, dict]:
        """Convert to DynamoDB item format."""
        pk = f"USER#{self.user_id}"
        sk = f"CHAR#{self.character_id}"
        data = self.model_dump(exclude={"user_id", "character_id"})
        return pk, sk, data

    @classmethod
    def from_db_item(cls, item: dict) -> "Character":
        """Create Character from DynamoDB item."""
        # Extract IDs from composite keys
        user_id = item["PK"].replace("USER#", "")
        character_id = item["SK"].replace("CHAR#", "")
        return cls(
            user_id=user_id,
            character_id=character_id,
            **{k: v for k, v in item.items() if k not in ("PK", "SK")},
        )


# Repository pattern example
class CharacterRepository:
    """Repository for character data operations."""

    def __init__(self, db: DynamoDBClient) -> None:
        """Initialize with DB client."""
        self.db = db

    def create(self, character: Character) -> Character:
        """Create a new character."""
        pk, sk, data = character.to_db_item()
        self.db.put_item(pk, sk, data)
        return character

    def get(self, user_id: str, character_id: str) -> Character | None:
        """Get a character by ID."""
        pk = f"USER#{user_id}"
        sk = f"CHAR#{character_id}"
        item = self.db.get_item(pk, sk)
        return Character.from_db_item(item) if item else None

    def list_for_user(self, user_id: str) -> list[Character]:
        """List all characters for a user."""
        pk = f"USER#{user_id}"
        items = self.db.query_by_pk(pk, sk_prefix="CHAR#")
        return [Character.from_db_item(item) for item in items]

    def delete(self, user_id: str, character_id: str) -> bool:
        """Delete a character."""
        pk = f"USER#{user_id}"
        sk = f"CHAR#{character_id}"
        return self.db.delete_item(pk, sk)
