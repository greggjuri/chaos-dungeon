"""DM Lambda handler for processing player actions."""

import json
from typing import Any

from aws_lambda_powertools import Logger, Metrics, Tracer
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
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError
from pydantic import ValidationError

from dm.models import ActionRequest
from dm.service import DMService
from shared.config import get_config
from shared.cost_guard import CostGuard, get_limit_message
from shared.db import DynamoDBClient
from shared.exceptions import GameStateError, NotFoundError
from shared.token_tracker import TokenTracker
from shared.utils import extract_user_id

# Import anthropic for error handling (only if using Claude)
try:
    import anthropic

    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

logger = Logger()
tracer = Tracer()
metrics = Metrics(namespace="ChaosDungeon")

config = get_config()
cors_config = CORSConfig(
    allow_origin=("https://chaos.jurigregg.com" if config.is_production else "*"),
    allow_headers=["Content-Type", "X-User-ID", "X-User-Id"],
)
app = APIGatewayRestResolver(cors=cors_config)

_service: DMService | None = None
_cost_guard: CostGuard | None = None


def get_cost_guard() -> CostGuard:
    """Get or create the CostGuard singleton."""
    global _cost_guard
    if _cost_guard is None:
        tracker = TokenTracker(config.table_name)
        _cost_guard = CostGuard(tracker)
    return _cost_guard


def get_service() -> DMService:
    """Get or create the DM service singleton."""
    global _service
    if _service is None:
        db = DynamoDBClient(config.table_name)
        tracker = TokenTracker(config.table_name)
        _service = DMService(db, token_tracker=tracker)
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

    # Check cost limits before AI call
    cost_guard = get_cost_guard()
    limit_status = cost_guard.check_limits(session_id)

    if not limit_status.allowed:
        logger.info(
            "Request blocked by cost limits",
            extra={
                "session_id": session_id,
                "reason": limit_status.reason,
                "global_usage": limit_status.global_usage,
                "session_usage": limit_status.session_usage,
            },
        )
        metrics.add_metric(name="LimitHits", unit=MetricUnit.Count, value=1)
        metrics.add_dimension(name="Reason", value=limit_status.reason or "unknown")
        return Response(
            status_code=429,
            content_type="application/json",
            body=json.dumps({
                "error": "limit_reached",
                "message": get_limit_message(limit_status.reason or ""),
            }),
        )

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
    # Bedrock errors (Mistral)
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "ThrottlingException":
            logger.warning("Bedrock rate limit exceeded")
            return Response(
                status_code=429,
                content_type="application/json",
                body='{"error": "Rate limit exceeded. Please try again later."}',
            )
        elif error_code in ("ServiceUnavailableException", "ModelTimeoutException"):
            logger.error(f"Bedrock service error: {e}")
            return Response(
                status_code=503,
                content_type="application/json",
                body='{"error": "DM temporarily unavailable"}',
            )
        else:
            logger.error(f"Bedrock error: {error_code} - {e}")
            return Response(
                status_code=500,
                content_type="application/json",
                body='{"error": "DM service error"}',
            )
    # Anthropic errors (Claude) - only if using Claude
    except Exception as e:
        if HAS_ANTHROPIC:
            if isinstance(e, anthropic.RateLimitError):
                logger.warning("Claude API rate limit exceeded")
                return Response(
                    status_code=429,
                    content_type="application/json",
                    body='{"error": "Rate limit exceeded. Please try again later."}',
                )
            elif isinstance(e, anthropic.APIConnectionError):
                logger.error(f"Claude API connection error: {e}")
                return Response(
                    status_code=503,
                    content_type="application/json",
                    body='{"error": "Service temporarily unavailable"}',
                )
            elif isinstance(e, anthropic.APIStatusError):
                logger.error(f"Claude API error: {e.status_code} - {e.message}")
                return Response(
                    status_code=500,
                    content_type="application/json",
                    body='{"error": "DM unavailable"}',
                )
        # Re-raise unknown exceptions
        raise


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Main Lambda entry point."""
    return app.resolve(event, context)
