"""``EngramMemoryProvider.identity_signature()``: the identity-mapping values the gateway folds
into its agent-cache key, read from engram.json without touching the network."""

import json

import pytest

from hermes_plugin_engram import EngramMemoryProvider


@pytest.fixture
def engram_json(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    path = tmp_path / "engram.json"

    def _write(**values):
        path.write_text(json.dumps({"apiKey": "k", **values}))
        return path

    return _write


def test_signature_uses_neutral_keys(engram_json):
    engram_json(workspace="team", peerName="eri", aiPeer="hermes", pinUserPeer=True, runtimePeerPrefix="tg_",
                userPeerAliases={"222": "bob", "111": "alice"}, sessionPeerPrefix=True, a2aSessions=False)

    sig = EngramMemoryProvider().identity_signature()

    assert sig == {
        "workspace": "team",
        "user_identity": "eri",
        "agent_identity": "hermes",
        "pin_user_identity": True,
        "runtime_identity_prefix": "tg_",
        "user_identity_aliases": [("111", "alice"), ("222", "bob")],
        "session_prefixing": [True, False],
        "a2a_sessions": False,
    }
    assert not any(k.startswith("engram") for k in sig)


def test_signature_tracks_edits_to_the_file(engram_json):
    provider = EngramMemoryProvider()
    engram_json(peerName="eri", pinUserPeer=True)
    assert provider.identity_signature()["pin_user_identity"] is True

    engram_json(peerName="eri", pinUserPeer=False)
    assert provider.identity_signature()["pin_user_identity"] is False


def test_signature_never_touches_the_network(engram_json, network_attempts):
    engram_json(peerName="eri")
    EngramMemoryProvider().identity_signature()
    assert network_attempts == []
