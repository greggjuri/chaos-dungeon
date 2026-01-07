"""Cost protection guard for AI requests."""

from dataclasses import dataclass

from aws_lambda_powertools import Logger

from .cost_limits import CostLimits
from .token_tracker import TokenTracker

logger = Logger(child=True)


@dataclass
class LimitStatus:
    """Status of token limits."""

    allowed: bool
    reason: str | None = None
    global_usage: int = 0
    session_usage: int = 0
    global_remaining: int = 0
    session_remaining: int = 0


class CostGuard:
    """Guards against exceeding token limits."""

    def __init__(self, tracker: TokenTracker | None = None):
        """Initialize guard with optional tracker.

        Args:
            tracker: TokenTracker instance. Creates one if not provided.
        """
        self.tracker = tracker or TokenTracker()
        self.limits = CostLimits()

    def check_limits(self, session_id: str) -> LimitStatus:
        """Check if request is allowed under current limits.

        Args:
            session_id: Current session ID

        Returns:
            LimitStatus indicating if request should proceed
        """
        global_usage = self.tracker.get_global_usage()
        session_usage = self.tracker.get_session_usage(session_id)

        global_total = global_usage["input_tokens"] + global_usage["output_tokens"]
        session_total = session_usage["input_tokens"] + session_usage["output_tokens"]

        global_remaining = self.limits.GLOBAL_DAILY_TOKENS - global_total
        session_remaining = self.limits.SESSION_DAILY_TOKENS - session_total

        # Check global limit
        if global_total >= self.limits.GLOBAL_DAILY_TOKENS:
            logger.warning(
                "Global daily limit reached",
                extra={
                    "global_tokens": global_total,
                    "limit": self.limits.GLOBAL_DAILY_TOKENS,
                },
            )
            return LimitStatus(
                allowed=False,
                reason="global_limit",
                global_usage=global_total,
                session_usage=session_total,
                global_remaining=0,
                session_remaining=session_remaining,
            )

        # Check session limit
        if session_total >= self.limits.SESSION_DAILY_TOKENS:
            logger.warning(
                "Session daily limit reached",
                extra={
                    "session_id": session_id,
                    "session_tokens": session_total,
                    "limit": self.limits.SESSION_DAILY_TOKENS,
                },
            )
            return LimitStatus(
                allowed=False,
                reason="session_limit",
                global_usage=global_total,
                session_usage=session_total,
                global_remaining=global_remaining,
                session_remaining=0,
            )

        # Log warning if approaching limits
        if global_total >= self.limits.GLOBAL_DAILY_TOKENS * self.limits.WARNING_THRESHOLD:
            logger.warning(
                "Approaching global daily limit",
                extra={
                    "global_tokens": global_total,
                    "limit": self.limits.GLOBAL_DAILY_TOKENS,
                    "percentage": round(
                        global_total / self.limits.GLOBAL_DAILY_TOKENS * 100, 1
                    ),
                },
            )

        return LimitStatus(
            allowed=True,
            global_usage=global_total,
            session_usage=session_total,
            global_remaining=global_remaining,
            session_remaining=session_remaining,
        )


def get_limit_message(reason: str) -> str:
    """Get in-game narrative message for limit hit.

    Args:
        reason: The limit type ('global_limit' or 'session_limit')

    Returns:
        A narrative message that fits the game world.
    """
    if reason == "global_limit":
        return (
            "**The dungeon grows silent...**\n\n"
            "*A strange exhaustion settles over the realm. "
            "The spirits that guide your adventure have grown weary "
            "and must rest until the morrow.*\n\n"
            "The Chaos Dungeon will awaken again at midnight UTC. "
            "Your progress has been saved."
        )

    if reason == "session_limit":
        return (
            "**You feel a strange fatigue...**\n\n"
            "*The magical energies that power your journey have been "
            "depleted for today. Rest now, brave adventurer.*\n\n"
            "Your session limit has been reached. "
            "Return tomorrow for more adventures, or start a new session."
        )

    return "The dungeon is temporarily unavailable. Please try again later."
