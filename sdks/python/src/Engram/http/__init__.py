"""HTTP client module for Engram SDK."""

from .async_client import AsyncEngramHTTPClient
from .client import EngramHTTPClient
from .exceptions import (
    APIError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    ConnectionError,
    EngramError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    ServerError,
    TimeoutError,
    UnprocessableEntityError,
)

__all__ = [
    # Errors
    "EngramError",
    "APIError",
    "BadRequestError",
    "AuthenticationError",
    "PermissionDeniedError",
    "NotFoundError",
    "ConflictError",
    "UnprocessableEntityError",
    "RateLimitError",
    "ServerError",
    "TimeoutError",
    "ConnectionError",
    # Clients
    "EngramHTTPClient",
    "AsyncEngramHTTPClient",
]
