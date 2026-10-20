"""Concurrency test for get_engram_client() — the TOCTOU race fix (#24759).

Proves the Engram client is constructed exactly once even when many threads
race the first call, by stubbing the SDK constructor and counting invocations.
"""

import sys
import threading
import types

import pytest

from hermes_plugin_engram import client as engram_client
from hermes_plugin_engram.client import (
    EngramClientConfig,
    get_engram_client,
    reset_engram_client,
)


@pytest.fixture(autouse=True)
def _reset_singleton():
    reset_engram_client()
    yield
    reset_engram_client()


def _install_fake_engram_sdk(monkeypatch, build_count, build_lock):
    """Make `from engram import Engram` resolve to a counting fake."""

    class _FakeEngram:
        def __init__(self, **kwargs):
            with build_lock:
                build_count["n"] += 1
            import time
            time.sleep(0.01)  # widen the race window
            self.kwargs = kwargs

    fake_mod = types.ModuleType("engram")
    fake_mod.Engram = _FakeEngram
    monkeypatch.setitem(sys.modules, "engram", fake_mod)
    # Skip the lazy-install path entirely.
    monkeypatch.setattr(
        engram_client, "_resolve_optional_float", lambda *a, **k: None, raising=False
    )


def test_get_engram_client_builds_once_under_concurrent_first_call(monkeypatch):
    build_count = {"n": 0}
    build_lock = threading.Lock()
    _install_fake_engram_sdk(monkeypatch, build_count, build_lock)

    config = EngramClientConfig(
        api_key="test-key",
        workspace_id="ws",
        environment="production",
    )

    barrier = threading.Barrier(20)
    results = []
    results_lock = threading.Lock()

    def worker():
        barrier.wait()
        c = get_engram_client(config)
        with results_lock:
            results.append(c)

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert build_count["n"] == 1, "Engram client must be constructed exactly once"
    assert len(results) == 20
    assert all(r is results[0] for r in results), "all threads share one client"


def test_reset_allows_rebuild(monkeypatch):
    build_count = {"n": 0}
    build_lock = threading.Lock()
    _install_fake_engram_sdk(monkeypatch, build_count, build_lock)

    config = EngramClientConfig(
        api_key="test-key", workspace_id="ws", environment="production"
    )

    c1 = get_engram_client(config)
    assert build_count["n"] == 1
    # Cached: no rebuild.
    assert get_engram_client(config) is c1
    assert build_count["n"] == 1

    reset_engram_client()
    c2 = get_engram_client(config)
    assert build_count["n"] == 2
    assert c2 is not c1


def test_missing_credentials_still_raises_before_build(monkeypatch):
    build_count = {"n": 0}
    build_lock = threading.Lock()
    _install_fake_engram_sdk(monkeypatch, build_count, build_lock)

    bad = EngramClientConfig(api_key="", base_url="", workspace_id="ws")
    with pytest.raises(ValueError):
        get_engram_client(bad)
    assert build_count["n"] == 0
