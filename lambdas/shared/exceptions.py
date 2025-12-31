"""Custom exceptions for Chaos Dungeon."""


class ChaosDungeonError(Exception):
    """Base exception for all game errors."""

    def __init__(self, message: str = "An error occurred") -> None:
        """Initialize exception with message.

        Args:
            message: Error message
        """
        self.message = message
        super().__init__(self.message)


class NotFoundError(ChaosDungeonError):
    """Resource not found."""

    def __init__(self, resource_type: str, resource_id: str) -> None:
        """Initialize not found error.

        Args:
            resource_type: Type of resource (e.g., "Character", "Session")
            resource_id: ID of the missing resource
        """
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(f"{resource_type} '{resource_id}' not found")


class ValidationError(ChaosDungeonError):
    """Request validation failed."""

    def __init__(self, message: str, field: str | None = None) -> None:
        """Initialize validation error.

        Args:
            message: Validation error message
            field: Optional field name that failed validation
        """
        self.field = field
        super().__init__(message)


class GameStateError(ChaosDungeonError):
    """Invalid game state transition."""

    def __init__(self, message: str, current_state: str | None = None) -> None:
        """Initialize game state error.

        Args:
            message: Error message describing the invalid transition
            current_state: Current state when error occurred
        """
        self.current_state = current_state
        super().__init__(message)


class ConfigurationError(ChaosDungeonError):
    """Configuration or environment error."""

    def __init__(self, message: str, config_key: str | None = None) -> None:
        """Initialize configuration error.

        Args:
            message: Error message
            config_key: Optional configuration key that caused the error
        """
        self.config_key = config_key
        super().__init__(message)
