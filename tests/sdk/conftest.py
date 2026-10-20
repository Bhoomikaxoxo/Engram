import sys
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

# Add the SDK src to the path to allow imports
sdk_src_path = Path(__file__).parent.parent.parent / "sdks" / "python" / "src"
sys.path.insert(0, str(sdk_src_path))

# This is a bit of a hack to make the main conftest discoverable
sys.path.insert(0, str(Path(__file__).parent.parent))

from sdks.python.src.engram.client import Engram  # noqa: E402


@pytest.fixture
def engram_sync_test_client(client: TestClient) -> Engram:
    """
    Returns a Engram SDK client configured to talk to the test API.
    Uses sync operations directly.
    """
    http_client = httpx.Client(
        transport=client._transport,  # pyright: ignore
        base_url=str(client.base_url),
        headers=client.headers,
    )

    engram_client = Engram(
        workspace_id="sdk-test-workspace-sync",
        base_url=str(client.base_url),
        http_client=http_client,
    )
    return engram_client


@pytest_asyncio.fixture
async def engram_async_test_client(client: TestClient):
    """
    Returns a Engram SDK client configured to talk to the test API.
    Uses .aio accessor for async operations.
    """
    # For sync workspace creation
    http_client = httpx.Client(
        transport=client._transport,  # pyright: ignore
        base_url=str(client.base_url),
        headers=client.headers,
    )

    engram_client = Engram(
        workspace_id="sdk-test-workspace-async",
        base_url=str(client.base_url),
        http_client=http_client,
    )
    # Warm the app via the TestClient transport before using ASGITransport.
    # This avoids running the same ASGI app concurrently across two event loops,
    # without mutating the Engram client's local metadata/config caches.
    res = client.post("/v3/workspaces", json={"id": engram_client.workspace_id})
    assert res.status_code in (200, 201)

    # Set up async HTTP client manually for the ASGI transport
    from sdks.python.src.engram.http import AsyncEngramHTTPClient

    async_httpx_client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=client.app),
        base_url=str(client.base_url),
        headers=client.headers,
    )
    async_http = AsyncEngramHTTPClient(
        base_url=str(client.base_url),
        api_key=None,
        http_client=async_httpx_client,
    )
    engram_client._async_http = async_http  # pyright: ignore

    try:
        yield engram_client
    finally:
        await async_httpx_client.aclose()


@pytest.fixture(params=["sync", "async"])
def client_fixture(
    request: pytest.FixtureRequest,
    engram_sync_test_client: Engram,
    engram_async_test_client: Engram,
) -> tuple[Engram, str]:
    if request.param == "sync":
        return engram_sync_test_client, "sync"
    return engram_async_test_client, "async"
