"""
Example Lambda handler pattern for Chaos Dungeon.

This demonstrates the standard structure for all Lambda handlers:
- AWS Lambda Powertools for logging and tracing
- Pydantic for request/response validation
- Proper error handling
- Type hints throughout
"""
from typing import Any

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.event_handler.exceptions import (
    BadRequestError,
    NotFoundError,
)
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import BaseModel, Field, ValidationError

# Initialize Powertools
logger = Logger()
tracer = Tracer()
app = APIGatewayRestResolver()


# Request/Response Models
class CreateItemRequest(BaseModel):
    """Request model for creating an item."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)


class ItemResponse(BaseModel):
    """Response model for item data."""

    id: str
    name: str
    description: str
    created_at: str


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    message: str


# Route Handlers
@app.get("/items/<item_id>")
@tracer.capture_method
def get_item(item_id: str) -> dict[str, Any]:
    """
    Get a single item by ID.

    Args:
        item_id: The item's unique identifier

    Returns:
        Item data as dictionary

    Raises:
        NotFoundError: If item doesn't exist
    """
    logger.info("Getting item", extra={"item_id": item_id})

    # Example: Fetch from DynamoDB
    item = fetch_item_from_db(item_id)
    if not item:
        raise NotFoundError(f"Item {item_id} not found")

    return ItemResponse(**item).model_dump()


@app.post("/items")
@tracer.capture_method
def create_item() -> dict[str, Any]:
    """
    Create a new item.

    Returns:
        Created item data

    Raises:
        BadRequestError: If request validation fails
    """
    try:
        request = CreateItemRequest(**app.current_event.json_body)
    except ValidationError as e:
        logger.warning("Validation failed", extra={"errors": e.errors()})
        raise BadRequestError(f"Invalid request: {e}")

    logger.info("Creating item", extra={"name": request.name})

    # Example: Save to DynamoDB
    item = save_item_to_db(request)

    return ItemResponse(**item).model_dump()


@app.delete("/items/<item_id>")
@tracer.capture_method
def delete_item(item_id: str) -> dict[str, Any]:
    """Delete an item by ID."""
    logger.info("Deleting item", extra={"item_id": item_id})

    success = delete_item_from_db(item_id)
    if not success:
        raise NotFoundError(f"Item {item_id} not found")

    return {"message": "Item deleted"}


# Lambda Entry Point
@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    """
    Main Lambda entry point.

    This is the function configured as the Lambda handler.
    All routing is handled by APIGatewayRestResolver.
    """
    return app.resolve(event, context)


# Helper Functions (normally in shared module)
def fetch_item_from_db(item_id: str) -> dict | None:
    """Fetch item from DynamoDB. Placeholder for example."""
    # In real code: use shared.db module
    return None


def save_item_to_db(request: CreateItemRequest) -> dict:
    """Save item to DynamoDB. Placeholder for example."""
    # In real code: use shared.db module
    return {
        "id": "generated-id",
        "name": request.name,
        "description": request.description,
        "created_at": "2025-01-01T00:00:00Z",
    }


def delete_item_from_db(item_id: str) -> bool:
    """Delete item from DynamoDB. Placeholder for example."""
    # In real code: use shared.db module
    return True
