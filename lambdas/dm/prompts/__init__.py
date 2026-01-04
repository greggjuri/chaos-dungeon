"""Prompt building utilities for the DM."""

from .campaigns import CAMPAIGN_PROMPTS
from .context import DMPromptBuilder
from .mistral_format import build_mistral_prompt, build_mistral_prompt_with_history
from .output_format import OUTPUT_FORMAT
from .rules import BECMI_RULES
from .system_prompt import build_compact_system_prompt, build_system_prompt

__all__ = [
    "DMPromptBuilder",
    "build_system_prompt",
    "build_compact_system_prompt",
    "build_mistral_prompt",
    "build_mistral_prompt_with_history",
    "BECMI_RULES",
    "CAMPAIGN_PROMPTS",
    "OUTPUT_FORMAT",
]
