"""Tests for the server-assigned ``uid`` on workspaces, peers and sessions."""

from typing import cast

import pytest

from sdks.python.src.engram.client import Engram
from sdks.python.src.engram.peer import Peer
from sdks.python.src.engram.session import Session


@pytest.mark.asyncio
async def test_workspace_uid(client_fixture: tuple[Engram, str]) -> None:
    """The client learns its workspace uid from its first API call."""
    engram_client, client_type = client_fixture

    assert engram_client.uid is None
    if client_type == "async":
        await engram_client.aio.get_metadata()
    else:
        engram_client.get_metadata()
    uid = engram_client.uid
    assert uid
    assert uid != engram_client.workspace_id


@pytest.mark.asyncio
async def test_peer_uid(client_fixture: tuple[Engram, str]) -> None:
    """Peers carry the same uid from get-or-create, list and refresh."""
    engram_client, client_type = client_fixture

    if client_type == "async":
        peer = await engram_client.aio.peer(id="test-uid-peer")
        listed = cast(list[Peer], (await engram_client.aio.peers()).items)
        unfetched = Peer("test-uid-peer", engram_client)
        assert unfetched.uid is None
        await unfetched.aio.refresh()
    else:
        peer = engram_client.peer(id="test-uid-peer")
        listed = cast(list[Peer], list(engram_client.peers()))
        unfetched = Peer("test-uid-peer", engram_client)
        assert unfetched.uid is None
        unfetched.refresh()

    assert peer.uid
    assert peer.uid != peer.id
    assert {p.id: p.uid for p in listed}[peer.id] == peer.uid
    assert unfetched.uid == peer.uid
    assert engram_client.uid  # peer calls ensure the workspace first


@pytest.mark.asyncio
async def test_session_uid(client_fixture: tuple[Engram, str]) -> None:
    """Sessions carry their uid; session peers carry theirs; clones get a new one."""
    engram_client, client_type = client_fixture

    if client_type == "async":
        peer = await engram_client.aio.peer(id="test-uid-session-peer")
        session = await engram_client.aio.session(id="test-uid-session")
        await session.aio.add_peers(peer)
        listed = cast(list[Session], (await engram_client.aio.sessions()).items)
        session_peers = await session.aio.peers()
        clone = await session.aio.clone()
    else:
        peer = engram_client.peer(id="test-uid-session-peer")
        session = engram_client.session(id="test-uid-session")
        session.add_peers(peer)
        listed = cast(list[Session], list(engram_client.sessions()))
        session_peers = session.peers()
        clone = session.clone()

    assert session.uid
    assert session.uid != session.id
    assert {s.id: s.uid for s in listed}[session.id] == session.uid
    assert [p.uid for p in session_peers] == [peer.uid]
    assert clone.uid
    assert clone.uid != session.uid
