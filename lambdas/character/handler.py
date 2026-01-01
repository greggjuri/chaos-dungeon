"""Character Lambda handler for CRUD operations."""
from typing import Any

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver, Response, CORSConfig
from aws_lambda_powertools.event_handler.exceptions import (
    BadRequestError,
    UnauthorizedError,
)
from aws_lambda_powertools.event_handler.exceptions import (
    NotFoundError as APINotFoundError,
)
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from character.models import CharacterCreateRequest, CharacterUpdateRequest
from character.service import CharacterService
from shared.config import get_config
from shared.db import DynamoDBClient
from shared.exceptions import NotFoundError
from shared.utils import extract_user_id

logger = Logger()
tracer = Tracer()
cors_config = CORSConfig(
    allow_origin="*",
    allow_headers=["Content-Type", "X-User-Id"],
    max_age=300
)
app = APIGatewayRestResolver(cors=cors_config)

# Initialize service lazily
_service: CharacterService | None = None


def get_service() -> CharacterService:
    """Get or create the character service instance."""
    global _service
    if _service is None:
        config = get_config()
        db = DynamoDBClient(config.table_name)
        _service = CharacterService(db)
    return _service


def reset_service() -> None:
    """Reset the service instance (for testing)."""
    global _service
    _service = None


def get_user_id() -> str:
    """Extract and validate user ID from headers.

    Returns:
        The user ID from the X-User-ID header

    Raises:
        UnauthorizedError: If header is missing or invalid
    """
    user_id = extract_user_id(app.current_event.headers)
    if not user_id:
        raise UnauthorizedError("Missing or invalid X-User-ID header")
    return user_id


@app.post("/characters")
@tracer.capture_method
def create_character() -> Response:
    """Create a new character.

    Returns:
        201 response with created character
    """
    user_id = get_user_id()

    try:
        body = app.current_event.json_body or {}
        request = CharacterCreateRequest(**body)
    except ValidationError as e:
        raise BadRequestError(str(e)) from None

    character = get_service().create_character(user_id, request)

    return Response(
        status_code=201,
        content_type="application/json",
        body=character,
    )


@app.get("/characters")
@tracer.capture_method
def list_characters() -> dict[str, Any]:
    """List all characters for the current user.

    Returns:
        200 response with character list
    """
    user_id = get_user_id()
    characters = get_service().list_characters(user_id)

    return {"characters": characters}


@app.get("/characters/<character_id>")
@tracer.capture_method
def get_character(character_id: str) -> dict[str, Any]:
    """Get full character details.

    Args:
        character_id: The character's ID

    Returns:
        200 response with character details
    """
    user_id = get_user_id()

    try:
        return get_service().get_character(user_id, character_id)
    except NotFoundError:
        raise APINotFoundError("Character not found") from None


@app.patch("/characters/<character_id>")
@tracer.capture_method
def update_character(character_id: str) -> dict[str, Any]:
    """Update a character (name only).

    Args:
        character_id: The character's ID

    Returns:
        200 response with updated character
    """
    user_id = get_user_id()

    try:
        body = app.current_event.json_body or {}
        request = CharacterUpdateRequest(**body)
    except ValidationError as e:
        raise BadRequestError(str(e)) from None

    try:
        return get_service().update_character(user_id, character_id, request)
    except NotFoundError:
        raise APINotFoundError("Character not found") from None


@app.delete("/characters/<character_id>")
@tracer.capture_method
def delete_character(character_id: str) -> Response:
    """Delete a character.

    Args:
        character_id: The character's ID

    Returns:
        204 response (no content)
    """
    user_id = get_user_id()

    try:
        get_service().delete_character(user_id, character_id)
        return Response(
            status_code=204,
            content_type="application/json",
            body=None,
        )
    except NotFoundError:
        raise APINotFoundError("Character not found") from None


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    """Main Lambda entry point.

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response
    """
    return app.resolve(event, context)
