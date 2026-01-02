"""DM Lambda handler for processing player actions."""

from typing import Any

import anthropic
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import (
    APIGatewayRestResolver,
    CORSConfig,
    Response,
)
from aws_lambda_powertools.event_handler.exceptions import (
    BadRequestError,
    UnauthorizedError,
)
from aws_lambda_powertools.event_handler.exceptions import (
    NotFoundError as APINotFoundError,
)
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from dm.models import ActionRequest
from dm.service import DMService
from shared.config import get_config
from shared.db import DynamoDBClient
from shared.exceptions import GameStateError, NotFoundError
from shared.utils import extract_user_id

logger = Logger()
tracer = Tracer()

config = get_config()
cors_config = CORSConfig(
    allow_origin=(
        "https://chaos.jurigregg.com" if config.is_production else "*"
    ),
    allow_headers=["Content-Type", "X-User-ID", "X-User-Id"],
)
app = APIGatewayRestResolver(cors=cors_config)

_service: DMService | None = None


def get_service() -> DMService:
    """Get or create the DM service singleton."""
    global _service
    if _service is None:
        db = DynamoDBClient(config.table_name)
        _service = DMService(db)
    return _service


def get_user_id() -> str:
    """Extract and validate user ID from request headers."""
    user_id = extract_user_id(app.current_event.headers)
    if not user_id:
        raise UnauthorizedError("User ID required")
    return user_id


@app.post("/sessions/<session_id>/action")
@tracer.capture_method
def post_action(session_id: str) -> Response:
    """Process a player action.

    Args:
        session_id: Session UUID from path

    Returns:
        Response with DM narrative and state changes
    """
    user_id = get_user_id()

    try:
        body = app.current_event.json_body or {}
        request = ActionRequest(**body)
    except ValidationError as e:
        error_msg = e.errors()[0].get("msg", "Invalid request")
        raise BadRequestError(error_msg) from None

    service = get_service()

    try:
        response = service.process_action(
            session_id=session_id,
            user_id=user_id,
            action=request.action,
        )
        return Response(
            status_code=200,
            content_type="application/json",
            body=response.model_dump_json(),
        )
    except NotFoundError as e:
        raise APINotFoundError(f"{e.resource_type.title()} not found") from None
    except GameStateError as e:
        raise BadRequestError(str(e)) from None
    except anthropic.RateLimitError:
        logger.warning("Claude API rate limit exceeded")
        return Response(
            status_code=429,
            content_type="application/json",
            body='{"error": "Rate limit exceeded. Please try again later."}',
        )
    except anthropic.APIConnectionError as e:
        logger.error(f"Claude API connection error: {e}")
        return Response(
            status_code=503,
            content_type="application/json",
            body='{"error": "Service temporarily unavailable"}',
        )
    except anthropic.APIStatusError as e:
        logger.error(f"Claude API error: {e.status_code} - {e.message}")
        return Response(
            status_code=500,
            content_type="application/json",
            body='{"error": "DM unavailable"}',
        )


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Main Lambda entry point."""
    return app.resolve(event, context)
