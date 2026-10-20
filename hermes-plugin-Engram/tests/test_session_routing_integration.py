"""Route against real repository/SessionDB state, without contacting Engram."""

import subprocess

import pytest

from agent import runtime_cwd
from hermes_state import SessionDB
from hermes_plugin_engram import EngramMemoryProvider
from hermes_plugin_engram.client import EngramClientConfig


@pytest.mark.parametrize("cwd_source", ["explicit", "context", "terminal"])
def test_provider_routes_by_logical_workspace(monkeypatch, tmp_path, cwd_source):
    launch = tmp_path / "launch"
    repo = tmp_path / "project"
    launch.mkdir()
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    child = repo / "src"
    child.mkdir()
    monkeypatch.chdir(launch)
    monkeypatch.setenv("TERMINAL_CWD", str(child if cwd_source == "terminal" else launch))
    token = runtime_cwd.set_session_cwd(str(child) if cwd_source == "context" else None)
    cfg = EngramClientConfig(session_strategy="per-repo", sessions={str(launch): "wrong-bucket"})
    try:
        key = EngramMemoryProvider()._resolve_session_key(
            cfg, "conversation", **({"cwd": str(child)} if cwd_source == "explicit" else {})
        )
    finally:
        runtime_cwd._SESSION_CWD.reset(token)
    assert key == repo.name
