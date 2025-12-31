"""Environment configuration for Lambda functions."""
import os
from dataclasses import dataclass

from .exceptions import ConfigurationError


@dataclass
class Config:
    """Application configuration loaded from environment variables."""

    table_name: str
    environment: str
    claude_secret_arn: str | None
    log_level: str

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables.

        Returns:
            Config instance with values from environment

        Raises:
            ConfigurationError: If required environment variables are missing
        """
        table_name = os.environ.get("TABLE_NAME")
        if not table_name:
            raise ConfigurationError(
                "TABLE_NAME environment variable is required",
                config_key="TABLE_NAME",
            )

        return cls(
            table_name=table_name,
            environment=os.environ.get("ENVIRONMENT", "dev"),
            claude_secret_arn=os.environ.get("CLAUDE_API_KEY_SECRET"),
            log_level=os.environ.get("POWERTOOLS_LOG_LEVEL", "INFO"),
        )

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "prod"


def get_config() -> Config:
    """Get cached configuration instance.

    Returns:
        Config instance (cached after first call)
    """
    if not hasattr(get_config, "_config"):
        get_config._config = Config.from_env()
    return get_config._config
