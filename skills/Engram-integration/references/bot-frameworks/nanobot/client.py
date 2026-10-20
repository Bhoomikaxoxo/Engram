"""Engram client initialization and configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from engram import Engram


@dataclass
class EngramConfig:
    """Configuration for Engram client."""

    workspace_id: str = "nanobot"
    api_key: str | None = None
    environment: str = "production"

    @classmethod
    def from_env(cls, workspace_id: str = "nanobot") -> EngramConfig:
        """Create config from environment variables."""
        return cls(
            workspace_id=workspace_id,
            api_key=os.environ.get("ENGRAM_API_KEY"),
            environment=os.environ.get("ENGRAM_ENVIRONMENT", "production"),
        )


_engram_client: Engram | None = None


def get_engram_client(config: EngramConfig | None = None) -> Engram:
    """
    Get or create the Engram client singleton.

    Args:
        config: Optional config. If not provided, uses environment variables.

    Returns:
        Configured Engram client.

    Raises:
        ValueError: If ENGRAM_API_KEY is not set.
    """
    global _engram_client

    if _engram_client is not None:
        return _engram_client

    if config is None:
        config = EngramConfig.from_env()

    if not config.api_key:
        raise ValueError(
            "ENGRAM_API_KEY environment variable is required. "
            "Get an API key from https://app.engram.dev"
        )

    try:
        from engram import Engram
    except ImportError:
        raise ImportError(
            "engram-ai is required for Engram integration. "
            "Install it with: nanobot engram enable --api-key YOUR_KEY"
        )

    logger.info(f"Initializing Engram client (workspace: {config.workspace_id})")

    _engram_client = Engram(
        workspace_id=config.workspace_id,
        api_key=config.api_key,
        environment=config.environment,
    )

    return _engram_client


def reset_engram_client() -> None:
    """Reset the Engram client singleton (useful for testing)."""
    global _engram_client
    _engram_client = None
