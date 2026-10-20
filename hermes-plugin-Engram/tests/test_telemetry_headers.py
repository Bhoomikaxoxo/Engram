"""Client-identity headers the plugin attaches to every Engram request."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import hermes_plugin_engram.client as client_mod
from hermes_plugin_engram.client import EngramClientConfig, get_engram_client, telemetry_headers


@pytest.fixture(autouse=True)
def _fresh_client_cache():
    client_mod.reset_engram_client()
    yield
    client_mod.reset_engram_client()


def test_plugin_header_carries_the_manifest_version(tmp_path, monkeypatch):
    (tmp_path / "plugin.yaml").write_text('name: engram\nversion: "9.8.7"\n')
    monkeypatch.setattr(client_mod, "__file__", str(tmp_path / "client.py"))

    assert telemetry_headers()["X-Engram-Plugin"] == "hermes-plugin-engram/9.8.7"


def test_plugin_header_matches_the_shipped_manifest():
    manifest = Path(client_mod.__file__).with_name("plugin.yaml").read_text()
    version = next(line.split(":", 1)[1].strip() for line in manifest.splitlines() if line.startswith("version:"))

    assert telemetry_headers()["X-Engram-Plugin"] == f"hermes-plugin-engram/{version}"


@pytest.mark.parametrize("manifest", [None, "name: engram\n", "version:\n"])
def test_plugin_header_falls_back_to_unknown(tmp_path, monkeypatch, manifest):
    if manifest is not None:
        (tmp_path / "plugin.yaml").write_text(manifest)
    monkeypatch.setattr(client_mod, "__file__", str(tmp_path / "client.py"))

    assert telemetry_headers()["X-Engram-Plugin"] == "hermes-plugin-engram/unknown"


def test_host_header_includes_the_hermes_version(monkeypatch):
    monkeypatch.setattr(client_mod, "_hermes_version", lambda: "0.21.3")

    assert telemetry_headers()["X-Engram-Host"] == f"hermes/0.21.3 ({sys.platform})"


def test_host_header_omits_an_unresolvable_hermes_version(monkeypatch):
    monkeypatch.setitem(sys.modules, "hermes_cli", None)  # makes `from hermes_cli import ...` raise

    assert client_mod._hermes_version() == ""
    assert telemetry_headers()["X-Engram-Host"] == f"hermes ({sys.platform})"


def test_built_client_sends_the_telemetry_headers():
    cfg = EngramClientConfig(api_key="k", base_url="http://localhost:8000", workspace_id="hermes")

    with patch("engram.Engram", return_value=MagicMock(name="Engram")) as mock_engram:
        get_engram_client(cfg)

    assert mock_engram.call_args.kwargs["default_headers"] == telemetry_headers()
