"""Cost protection limit configuration."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CostLimits:
    """Token limits for cost protection.

    These limits prevent runaway costs from AI API calls.
    Limits reset at midnight UTC daily.
    """

    # Global daily limit (all users combined)
    # 500K tokens @ $1/$3 per 1M ≈ $1.10/day max
    GLOBAL_DAILY_TOKENS: int = 500_000

    # Per-session daily limit (single user session)
    # Prevents one user from consuming entire budget
    SESSION_DAILY_TOKENS: int = 50_000

    # Per-request output limit (sanity check)
    MAX_OUTPUT_TOKENS: int = 2_000

    # Warning threshold (log warning at this %)
    WARNING_THRESHOLD: float = 0.8
