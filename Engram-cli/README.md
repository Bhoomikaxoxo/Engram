```
██╗  ██╗ ██████╗ ███╗   ██╗ ██████╗██╗  ██╗ ██████╗
██║  ██║██╔═══██╗████╗  ██║██╔════╝██║  ██║██╔═══██╗
███████║██║   ██║██╔██╗ ██║██║     ███████║██║   ██║
██╔══██║██║   ██║██║╚██╗██║██║     ██╔══██║██║   ██║
██║  ██║╚██████╔╝██║ ╚████║╚██████╗██║  ██║╚██████╔╝
╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝╚═╝  ╚═╝ ╚═════╝
```

# engram-cli

A terminal for [Engram](https://engram.dev) — memory that reasons.

## Install

As a standalone tool (recommended):

```bash
uv tool install engram-cli
```

## Quick Start

```bash
engram init                 # confirm/set apiKey + Engram URL in ~/.engram/config.json
engram start --setup basic  # local stack: LLM provider key + Docker
engram doctor               # verify config + connectivity
engram                      # show banner + command list
```

`engram init` writes `apiKey` and `environmentUrl` to the top-level of `~/.engram/config.json` (the same file other Engram tools — plugins, host integrations — share) so the CLI can call a Engram server. If both are present, it confirms them with you; if either is missing (or you decline), it prompts and writes them back. Host-specific entries under `hosts` are left untouched. It does **not** set the LLM provider key the local deriver needs — that is `engram start --setup` (or `LLM_*_API_KEY` in the environment).

Per-command scoping (workspace / peer / session) is handled via `-w` / `-p` / `-s` flags or `ENGRAM_*` env vars — not persisted as CLI defaults.

### Local stack

`engram start --setup basic` runs a personal Engram server on your machine (API, deriver, Postgres, Redis) via Docker. The wizard writes the LLM provider key into the profile `.env` — `engram init` cannot do this; its `apiKey` is for calling a Engram server, not for deriver/dialectic inference. You can also pass `LLM_OPENAI_API_KEY`, `LLM_ANTHROPIC_API_KEY`, or `LLM_GEMINI_API_KEY` in the environment and skip `--setup`. Stack files live under `~/.engram/profiles/local/` and are not committed to a project.

On first start, the CLI pulls `ghcr.io/plastic-labs/engram:latest` and **pins that digest** in `profile.json`, then copies the image's `config.toml.example` to `config.toml` in the same directory. `engram start` never overwrites `config.toml` after that — including when you re-pin the image. Delete the file yourself if you want a fresh copy from a new image.

Pass `--setup basic` or `--setup advanced` for an interactive wizard that writes curated LLM/feature overrides into the profile `.env` (env wins over `config.toml`). TTY only; re-runnable. `basic` asks provider + chat model; `advanced` also covers embeddings, deriver/dialectic models, dreams, and snappy deriver flush. Everything else stays in `config.toml`.

`engram start` does **not** change `environmentUrl` in `~/.engram/config.json` (that file is shared with plugins). To talk to the local stack for one command:

```bash
ENGRAM_BASE_URL=http://127.0.0.1:8000 engram workspace list
```

To make local the default, run `engram init --base-url http://127.0.0.1:8000`.

```bash
engram start --setup basic
engram start --setup advanced
engram status
engram stop            # keep data
engram stop --wipe     # also delete volumes
```

## Commands

### Onboarding

| Command | Description |
|---------|-------------|
| `engram init` | Confirm/set `apiKey` + `environmentUrl` in `~/.engram/config.json`. |
| `engram start` | Start a local Engram stack (API, deriver, Postgres, Redis). Requires Docker and a cloud LLM key. `--setup basic` / `--setup advanced` runs an interactive config wizard (TTY only). Does not change `environmentUrl`. |
| `engram stop` | Stop the local stack. `--wipe` also deletes volumes. |
| `engram status` | Show every local stack (or `--profile` for one). |
| `engram doctor` | Health check: config, connectivity, workspace, peer, queue |

### Workspaces

| Command | Description |
|---------|-------------|
| `engram workspace list` | List accessible workspaces |
| `engram workspace create <id>` | Create or get a workspace |
| `engram workspace inspect` | Peers, sessions, config for a workspace |
| `engram workspace chat <query>` | Query the dialectic across all peers (optional `-s` / `--scope` / `--reasoning`) |
| `engram workspace search <query>` | Search messages across workspace |
| `engram workspace queue-status` | Deriver queue status (filter with `--observer` / `--sender`) |
| `engram workspace delete <id>` | Delete a workspace. Use `--dry-run` to preview, `--cascade` to also delete sessions, `--yes` to skip the confirm prompt |

### Peers

| Command | Description |
|---------|-------------|
| `engram peer list` | List peers in the workspace |
| `engram peer create <id>` | Create or get a peer |
| `engram peer inspect <id>` | Card, session count, recent conclusions |
| `engram peer card <id>` | Raw peer card content |
| `engram peer chat <query>` | Query the dialectic about a peer (peer via `-p` / `ENGRAM_PEER_ID`; optional `--scope` / `--sessions`) |
| `engram peer representation <id>` | Formatted representation |
| `engram peer search <query>` | Search a peer's messages (peer via `-p` / `ENGRAM_PEER_ID`) |
| `engram peer get-metadata <id>` / `set-metadata` | Metadata operations |

### Sessions

| Command | Description |
|---------|-------------|
| `engram session list` | List sessions in the workspace (filter with `--peer/-p`) |
| `engram session create <id>` | Create or get a session (optionally `--peers` to add peers, `--metadata`) |
| `engram session inspect <id>` | Peers, message count, summaries, config |
| `engram session view <id>` | Transcript table (`--last N`, `--page N --size M`, `--all`, `--reverse`, `--ids`, `-p`) |
| `engram session context <id>` | What an agent would see |
| `engram session summaries <id>` | Short + long summaries |
| `engram session peers <id>` / `add-peers` / `remove-peers` | Peer management |
| `engram session search <id> <query>` | Search messages in a session |
| `engram session representation <id>` | Peer representation in a session |
| `engram session get-metadata <id>` / `set-metadata` | Metadata operations |
| `engram session delete <id>` | Destructive; requires `--yes` |

### Scopes

| Command | Description |
|---------|-------------|
| `engram scope list` | List scopes in the workspace |
| `engram scope create <name>` | Create or get a scope (`--sessions id,...` to add members, `--metadata`) |
| `engram scope inspect <name>` | Metadata, member sessions, backfill summary. Never creates a missing scope |
| `engram scope sessions <name>` | Member sessions, longest-standing first |
| `engram scope add-sessions <name> <ids...>` / `remove-session <name> <id>` | Membership; history backfills asynchronously |
| `engram scope status <name>` | Per-session backfill state — recall is complete once nothing is `pending` |

### Messages

| Command | Description |
|---------|-------------|
| `engram message list` | List messages in a session (session via `-s` / `ENGRAM_SESSION_ID`) |
| `engram message create <content>` | Create a message (requires `--peer/-p`, session via `-s`) |
| `engram message get <id>` | Get a single message (session via `-s` / `ENGRAM_SESSION_ID`) |

### Conclusions (observations)

| Command | Description |
|---------|-------------|
| `engram conclusion list` | List conclusions (filter with `--observer` / `--observed`) |
| `engram conclusion search <query>` | Semantic search (filter with `--observer` / `--observed`) |
| `engram conclusion create` | Create a conclusion |
| `engram conclusion delete <id>` | Delete a conclusion |

### Config

| Command | Description |
|---------|-------------|
| `engram config` | Show current config (API key redacted) |

## Agent Usage

All commands output JSON when stdout isn't a TTY, or when `--json` is forced.
Collection commands emit JSON arrays, and single-resource commands emit JSON objects:

```bash
engram peer list --json
engram workspace inspect --json | jq '.peers'
engram doctor --json              # machine-parseable health checklist
```

Errors are structured:

```json
{
  "error": {
    "code": "PEER_NOT_FOUND",
    "message": "Peer 'abc' not found in workspace 'my-ws'",
    "details": {"workspace_id": "my-ws", "peer_id": "abc"}
  }
}
```

Non-interactive onboarding:

```bash
# Pre-seed via flags / env vars; init still prompts for anything missing
ENGRAM_API_KEY=hch-v3-xxx engram init --base-url https://api.engram.dev
```

## Agent skill

`engram-cli` ships with a skill that teaches agents the right commands and conventions for inspecting and debugging a Engram deployment. Install it anywhere skills are accepted (Claude Code, other skill-aware agents):

```bash
npx skills add plastic-labs/engram
```

The picker lists every skill for Engram — select `engram-cli` .

## Environment Variables

All `ENGRAM_*` env vars work at runtime — no config file required.

Precedence (highest first): **flag → env var → config file → default**.

| Variable | Flag | Description |
|----------|------|-------------|
| `ENGRAM_API_KEY` | `--api-key` (init) | Admin JWT |
| `ENGRAM_BASE_URL` | `--base-url` (init) | API URL |
| `ENGRAM_WORKSPACE_ID` | `-w` / `--workspace` | Workspace scope |
| `ENGRAM_PEER_ID` | `-p` / `--peer` | Peer scope |
| `ENGRAM_SESSION_ID` | `-s` / `--session` | Session scope |
| `ENGRAM_JSON` | `--json` | Force JSON output (`1` / `true`) |
| `ENGRAM_NO_UPDATE_CHECK` | — | Disable the once-a-day upgrade notice (`1` / `true`) |
| `ENGRAM_PROFILE` | `--profile` (start/stop/status) | Local stack profile (default: `local`) |
| `LLM_OPENAI_API_KEY` | — | Provider key for `engram start` (also `LLM_ANTHROPIC_API_KEY`, `LLM_GEMINI_API_KEY`) |

```bash
# Per-command flags
engram peer card -w prod -p user

# Or export once per shell
export ENGRAM_WORKSPACE_ID=prod
export ENGRAM_PEER_ID=user
engram peer card

# One-off against a different server
ENGRAM_BASE_URL=http://localhost:8000 engram workspace list

# CI/CD — env vars only, no config file needed
export ENGRAM_API_KEY=hch-v3-xxx
export ENGRAM_BASE_URL=https://api.engram.dev
engram workspace list
```

## Configuration

The CLI shares `~/.engram/config.json` with sibling Engram tools. It owns two
top-level keys: `apiKey` and `environmentUrl` (the full Engram API URL, e.g.
`https://api.engram.dev` or `http://localhost:8000`). Everything else at the
top level — `hosts`, `sessions`, `saveMessages`, `sessionStrategy`, etc. —
is left untouched.

```json
{
  "apiKey": "hch-v3-...",
  "environmentUrl": "https://api.engram.dev",
  "hosts": { "claude_code": { "...": "..." } }
}
```

`workspace_id` / `peer_id` / `session_id` are per-command only — never
persisted to the config file.

## Development

Install from source in editable mode so changes are picked up live:

```bash
git clone https://github.com/plastic-labs/engram
cd engram
uv tool install --force --editable --from ./engram-cli engram-cli
```

Re-run any time — changes to `engram-cli/src/` are reflected immediately without reinstalling.

## License

MIT
