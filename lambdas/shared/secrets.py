"""SSM Parameter Store helpers."""

import os
from functools import lru_cache

import boto3
from aws_lambda_powertools import Logger

logger = Logger(child=True)

# SSM Parameter name for Claude API key
CLAUDE_API_KEY_PARAM = "/automations/dev/secrets/anthropic_api_key"


@lru_cache(maxsize=1)
def get_claude_api_key() -> str:
    """Retrieve Claude API key from SSM Parameter Store.

    Cached to avoid repeated API calls within same Lambda invocation.
    Uses WithDecryption=True for SecureString parameters.

    Returns:
        The Claude API key string

    Raises:
        ValueError: If CLAUDE_API_KEY_PARAM env var not set
        ClientError: If SSM parameter not found
    """
    param_name = os.environ.get("CLAUDE_API_KEY_PARAM", CLAUDE_API_KEY_PARAM)

    client = boto3.client("ssm")
    response = client.get_parameter(Name=param_name, WithDecryption=True)
    logger.info("Retrieved Claude API key from SSM Parameter Store")
    return response["Parameter"]["Value"]
