"""Engram client initialization for Zo Computer skill."""

import os

from dotenv import load_dotenv
from engram import Engram

load_dotenv()


def get_client(workspace_id: str | None = None) -> Engram:
    """Initialize and return a Engram client.

    Reads ENGRAM_API_KEY and ENGRAM_WORKSPACE_ID from environment variables.
    The workspace_id parameter overrides the environment variable if provided.

    Args:
        workspace_id: Optional workspace ID override. Falls back to the
            ENGRAM_WORKSPACE_ID env var, then to "default".

    Returns:
        Configured Engram client instance.
    """
    api_key = os.getenv("ENGRAM_API_KEY")
    if not api_key:
        raise ValueError(
            "ENGRAM_API_KEY is required. Set it in your environment or .env file."
        )

    env_workspace = os.getenv("ENGRAM_WORKSPACE_ID")
    resolved_workspace = workspace_id or env_workspace or "default"
    return Engram(api_key=api_key, workspace_id=resolved_workspace)
