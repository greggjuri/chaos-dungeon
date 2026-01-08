"""Bedrock client for Mistral model invocation."""

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

import boto3
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError

if TYPE_CHECKING:
    from mypy_boto3_bedrock_runtime import BedrockRuntimeClient

logger = Logger(child=True)

MODEL_ID = "mistral.mistral-small-2402-v1:0"


@dataclass
class MistralResponse:
    """Response from Mistral invocation with usage stats."""

    text: str
    input_tokens: int
    output_tokens: int


class BedrockClient:
    """Wrapper for Mistral via AWS Bedrock."""

    def __init__(self, region: str = "us-east-1"):
        """Initialize Bedrock client.

        Args:
            region: AWS region for Bedrock
        """
        self.client: BedrockRuntimeClient = boto3.client(
            "bedrock-runtime", region_name=region
        )

    def invoke_mistral(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.8,
        top_p: float = 0.95,
    ) -> MistralResponse:
        """Invoke Mistral Small via Bedrock.

        Args:
            prompt: Full prompt including system and user content
            max_tokens: Maximum response tokens
            temperature: Sampling temperature (0-1)
            top_p: Top-p sampling parameter

        Returns:
            MistralResponse with text and estimated token counts

        Raises:
            ClientError: Bedrock API errors
        """
        body = json.dumps(
            {
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
            }
        )

        try:
            response = self.client.invoke_model(
                modelId=MODEL_ID,
                body=body,
                contentType="application/json",
                accept="application/json",
            )

            result = json.loads(response["body"].read())
            output_text = result["outputs"][0]["text"]

            # Log usage metrics (estimate tokens from response length)
            # Mistral doesn't return token counts, so we estimate
            input_tokens = int(len(prompt.split()) * 1.3)  # rough estimate
            output_tokens = int(len(output_text.split()) * 1.3)

            # Calculate estimated cost (Mistral Small: $1/$3 per M tokens)
            estimated_cost = (input_tokens * 1.0 / 1_000_000) + (
                output_tokens * 3.0 / 1_000_000
            )

            logger.info(
                "Bedrock Mistral usage",
                extra={
                    "model": MODEL_ID,
                    "estimated_input_tokens": input_tokens,
                    "estimated_output_tokens": output_tokens,
                    "estimated_cost_usd": round(estimated_cost, 6),
                },
            )

            return MistralResponse(
                text=output_text,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(
                "Bedrock API error",
                extra={
                    "error_code": error_code,
                    "error_message": str(e),
                },
            )
            raise

    def send_action(
        self,
        system_prompt: str,
        context: str,
        action: str,
    ) -> MistralResponse:
        """Send player action to Mistral, return response with usage stats.

        Matches ClaudeClient interface for easy swapping.

        Args:
            system_prompt: The DM system prompt
            context: Dynamic context (character, session state)
            action: Player's action text

        Returns:
            MistralResponse with text and token usage
        """
        from dm.prompts.mistral_format import build_mistral_prompt

        prompt = build_mistral_prompt(
            system_prompt=system_prompt,
            context=context,
            action=action,
        )

        return self.invoke_mistral(
            prompt=prompt,
            max_tokens=800,  # Reduced for cost
            temperature=0.8,
        )

    def narrate_combat(
        self,
        system_prompt: str,
        combat_actions: str,
    ) -> MistralResponse:
        """Generate combat narrative from mechanical results.

        Uses a simpler prompt format optimized for narrative generation
        without the DM response wrapper that can leak.

        Args:
            system_prompt: The narrator system prompt
            combat_actions: Mechanical description of what happened

        Returns:
            MistralResponse with narrative text
        """
        # Simple prompt without "Respond as the Dungeon Master" wrapper
        prompt = f"<s>[INST] {system_prompt}\n\n{combat_actions} [/INST]"

        return self.invoke_mistral(
            prompt=prompt,
            max_tokens=200,  # Short narrative only
            temperature=0.7,  # Slightly more focused
        )
