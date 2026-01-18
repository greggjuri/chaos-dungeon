"""Session Lambda handler for CRUD operations."""

from typing import Any

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver, CORSConfig, Response
from aws_lambda_powertools.event_handler.exceptions import (
    BadRequestError,
    UnauthorizedError,
)
from aws_lambda_powertools.event_handler.exceptions import (
    NotFoundError as APINotFoundError,
)
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from session.models import SessionCreateRequest
from session.service import SessionService
from shared.config import get_config
from shared.db import DynamoDBClient
from shared.exceptions import ConflictError, NotFoundError
from shared.utils import extract_user_id

logger = Logger()
tracer = Tracer()
cors_config = CORSConfig(allow_origin="*", allow_headers=["Content-Type", "X-User-Id"], max_age=300)
app = APIGatewayRestResolver(cors=cors_config)

# Initialize service lazily
_service: SessionService | None = None


def get_service() -> SessionService:
    """Get or create the session service instance."""
    global _service
    if _service is None:
        config = get_config()
        db = DynamoDBClient(config.table_name)
        _service = SessionService(db)
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


@app.post("/sessions")
@tracer.capture_method
def create_session() -> Response:
    """Create a new game session.

    Returns:
        201 response with created session
    """
    user_id = get_user_id()

    try:
        body = app.current_event.json_body or {}
        request = SessionCreateRequest(**body)
    except ValidationError as e:
        raise BadRequestError(str(e)) from None

    try:
        session = get_service().create_session(user_id, request)
    except NotFoundError:
        raise APINotFoundError("Character not found") from None
    except ConflictError as e:
        return Response(
            status_code=409,
            content_type="application/json",
            body={"error": e.message},
        )

    return Response(
        status_code=201,
        content_type="application/json",
        body=session,
    )


@app.get("/sessions")
@tracer.capture_method
def list_sessions() -> dict[str, Any]:
    """List all sessions for the current user.

    Returns:
        200 response with session list
    """
    user_id = get_user_id()

    # Get optional query parameters
    params = app.current_event.query_string_parameters or {}
    character_id = params.get("character_id")
    limit_str = params.get("limit", "20")

    try:
        limit = min(int(limit_str), 50)  # Cap at 50
    except ValueError:
        limit = 20

    sessions = get_service().list_sessions(user_id, character_id, limit)

    return {"sessions": sessions}


@app.get("/sessions/<session_id>")
@tracer.capture_method
def get_session(session_id: str) -> dict[str, Any]:
    """Get full session details.

    Args:
        session_id: The session's ID

    Returns:
        200 response with session details
    """
    user_id = get_user_id()

    try:
        return get_service().get_session(user_id, session_id)
    except NotFoundError:
        raise APINotFoundError("Session not found") from None


@app.get("/sessions/<session_id>/history")
@tracer.capture_method
def get_message_history(session_id: str) -> dict[str, Any]:
    """Get paginated message history.

    Args:
        session_id: The session's ID

    Returns:
        200 response with message history
    """
    user_id = get_user_id()

    # Get optional query parameters
    params = app.current_event.query_string_parameters or {}
    before = params.get("before")
    limit_str = params.get("limit", "20")

    try:
        limit = min(int(limit_str), 100)  # Cap at 100
    except ValueError:
        limit = 20

    try:
        return get_service().get_message_history(user_id, session_id, limit, before)
    except NotFoundError:
        raise APINotFoundError("Session not found") from None


@app.delete("/sessions/<session_id>")
@tracer.capture_method
def delete_session(session_id: str) -> Response:
    """Delete a session.

    Args:
        session_id: The session's ID

    Returns:
        204 response (no content)
    """
    user_id = get_user_id()

    try:
        get_service().delete_session(user_id, session_id)
        return Response(
            status_code=204,
            content_type="application/json",
            body=None,
        )
    except NotFoundError:
        raise APINotFoundError("Session not found") from None


@app.patch("/sessions/<session_id>/options")
@tracer.capture_method
def update_options(session_id: str) -> dict[str, Any]:
    """Update session options.

    Args:
        session_id: The session's ID

    Returns:
        200 response with updated options
    """
    from shared.models import GameOptions

    user_id = get_user_id()

    try:
        body = app.current_event.json_body or {}
        options = GameOptions(**body)
    except ValidationError as e:
        raise BadRequestError(str(e)) from None

    try:
        return get_service().update_options(user_id, session_id, options)
    except NotFoundError:
        raise APINotFoundError("Session not found") from None


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
