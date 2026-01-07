"""Claude API client with prompt caching."""

import anthropic
from aws_lambda_powertools import Logger

from dm.bedrock_client import MistralResponse

logger = Logger(child=True)


class ClaudeClient:
    """Wrapper for Claude API with prompt caching."""

    MODEL = "claude-3-haiku-20240307"
    MAX_TOKENS = 1024

    def __init__(self, api_key: str):
        """Initialize Claude client.

        Args:
            api_key: Anthropic API key
        """
        self.client = anthropic.Anthropic(api_key=api_key)

    def send_action(
        self,
        system_prompt: str,
        context: str,
        action: str,
    ) -> MistralResponse:
        """Send player action to Claude, return response with usage stats.

        Uses prompt caching on system_prompt for cost savings.

        Args:
            system_prompt: The DM system prompt (cacheable)
            context: Dynamic context (character, session state)
            action: Player's action text

        Returns:
            MistralResponse with text and token usage
        """
        response = self.client.messages.create(
            model=self.MODEL,
            max_tokens=self.MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": f"{context}\n\n[Player Action]: {action}",
                }
            ],
        )

        # Log cache performance and cost metrics
        usage = response.usage
        cache_creation = getattr(usage, "cache_creation_input_tokens", 0)
        cache_read = getattr(usage, "cache_read_input_tokens", 0)

        # Calculate estimated cost
        estimated_cost = (
            (usage.input_tokens * 0.25 / 1_000_000)
            + (usage.output_tokens * 1.25 / 1_000_000)
            + (cache_read * 0.025 / 1_000_000)  # 90% discount on cached
        )

        logger.info(
            "Claude API usage",
            extra={
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cache_creation_input_tokens": cache_creation,
                "cache_read_input_tokens": cache_read,
                "estimated_cost_usd": round(estimated_cost, 6),
            },
        )

        return MistralResponse(
            text=response.content[0].text,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
        )
