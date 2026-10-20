"""`engram.get_scope()` looks a scope up without the get-or-create side effect."""

import pytest

from sdks.python.src.engram.client import Engram
from sdks.python.src.engram.http.exceptions import NotFoundError


@pytest.mark.asyncio
async def test_get_scope_returns_existing_without_creating_missing(
    client_fixture: tuple[Engram, str],
):
    engram_client, client_type = client_fixture

    if client_type == "async":
        created = await engram_client.aio.scope("lookup-me", metadata={"k": "v"})
        found = await engram_client.aio.get_scope("lookup-me")
        with pytest.raises(NotFoundError):
            await engram_client.aio.get_scope("never-created")
        listed = {s.id for s in (await engram_client.aio.scopes()).items}
    else:
        created = engram_client.scope("lookup-me", metadata={"k": "v"})
        found = engram_client.get_scope("lookup-me")
        with pytest.raises(NotFoundError):
            engram_client.get_scope("never-created")
        listed = {s.id for s in engram_client.scopes().items}

    assert found.id == created.id
    assert found.metadata == {"k": "v"}
    assert found.created_at == created.created_at
    # The failed lookup must not have provisioned the scope as a side effect.
    assert "never-created" not in listed
