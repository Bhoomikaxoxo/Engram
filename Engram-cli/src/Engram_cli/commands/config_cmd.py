"""Config inspection command: ``engram config``.

Writing to ``~/.engram/config.json`` is done only via ``engram init``, which
manages the two CLI-owned keys (``apiKey`` + ``environmentUrl``).
Workspace / peer / session scoping is per-command via flags / env vars, not
persisted defaults.
"""

from __future__ import annotations

import typer

from engram_cli._help import EngramTyperGroup
from engram_cli.common import handle_cmd_flags
from engram_cli.config import CLIConfig
from engram_cli.output import print_result

app = typer.Typer(cls=EngramTyperGroup, help="Inspect CLI configuration.", invoke_without_command=True)


@app.callback(invoke_without_command=True)
def config(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Force JSON output"),
) -> None:
    """Show current config (api key redacted)."""
    if ctx.invoked_subcommand is not None:
        return
    handle_cmd_flags(json_output=json_output)
    cfg = CLIConfig.load()
    print_result(cfg.redacted())
