---
name: engram-cli
description: Inspect and debug Engram workspaces via the `engram` CLI. Use when investigating peer representations, memory state, session context, or dialectic quality — any task that requires introspection of a Engram deployment, including verifying that a recall/record memory loop is actually working.
allowed-tools: Bash(engram:*), Bash(jq:*), Read, Grep
---

# Engram CLI

`engram` wraps the Engram Python SDK with agent-friendly defaults: JSON output, structured errors, input validation. Use it to inspect workspace state, debug peer memory, and diagnose the dialectic.

## Output & config

- **TTY**: human-readable tables (default when interactive)
- **Piped / `--json`**: JSON — collection commands emit arrays, single-resource commands emit objects
- **Exit codes**: `0` success · `1` client error (bad input, not found) · `2` server error · `3` auth error
- **Config**: `~/.engram/config.json` (shared with other Engram tools). The CLI owns `apiKey` and `environmentUrl` at the top level; run `engram init` to confirm or set them. Per-command scope (workspace / peer / session) is via `-w` / `-p` / `-s` flags or `ENGRAM_*` env vars.

## Command groups

- `engram config` — CLI configuration
- `engram start` / `stop` / `status` — local Docker stack (does not change `environmentUrl`). First start pins the Engram image digest and writes `config.toml` into the profile. Pass `--setup basic` or `--setup advanced` for an interactive config wizard (TTY only; writes `.env` overrides). `engram status` lists every profile; pass `--profile` for one.
- `engram workspace` — inspect, delete, search, chat
- `engram peer` — inspect, card, chat, search
- `engram session` — inspect, view (transcript), context, summaries
- `engram scope` — list, create, inspect, sessions, add-sessions, remove-session, status
- `engram message` — list and get
- `engram conclusion` — list, search, create, delete

## Rules

- Always pass `--json` when processing output programmatically.
- Run `engram peer inspect` before `engram peer chat` to understand context.
- Use `engram session context` to see exactly what an agent receives.
- Never run `engram workspace delete` without `engram workspace inspect` first.
- Compare peer card with conclusions to understand memory state.
- After `engram scope add-sessions`, check `engram scope status <name>` before a scoped `chat`: a `pending` backfill means the scope has not caught up yet, not that there is nothing to recall.
- `engram start` does not rewrite `environmentUrl`. Use `ENGRAM_BASE_URL=http://127.0.0.1:8000` to talk to local stack.

## Inspection tour

When orienting to a Engram deployment, walk outside-in:

### 1. Understand the workspace

```bash
engram workspace inspect --json
```

### 2. Find the peer

```bash
engram peer list --json
engram peer inspect <peer_id> --json
```

### 3. Check peer's memory

```bash
engram peer card <peer_id> --json
engram conclusion list --observer <peer_id> --json
engram conclusion search "topic" --observer <peer_id> --json
```

### 4. Debug a session

```bash
engram session inspect <session_id> --json
engram session view <session_id> --last 20 --json
engram session view <session_id> --page 2 --size 50 --json
engram message list <session_id> --last 20 --json
engram session context <session_id> --json
engram session summaries <session_id> --json
```

### 5. Search across workspace

```bash
engram workspace search "query" --json
engram workspace chat "what themes show up across peers?" --json
engram workspace chat "what happened in this project?" --scope my-project --json
engram peer search <peer_id> "query" --json
```

### 6. Bound recall with a scope

```bash
engram scope list --json
engram scope inspect <name> --json                       # members + backfill summary
engram scope create <name> --sessions <id1>,<id2> --json
engram scope status <name> --json                        # wait until nothing is pending
engram workspace chat "what happened here?" --scope <name> --json
```

## Debugging playbook

### Peer not learning?

```bash
# Is observation enabled?
engram peer inspect <peer_id> --json | jq '.configuration'

# What conclusions exist?
engram conclusion list --observer <peer_id> --json
engram conclusion search "expected topic" --observer <peer_id> --json
```

### Session context looks wrong?

```bash
# Raw context an agent would receive
engram session context <session_id> --json

# Summaries feeding the context
engram session summaries <session_id> --json

# Recent message history
engram message list <session_id> --last 50 --json
```

### Dialectic giving bad answers?

```bash
# What the peer card says
engram peer card <peer_id> --json

# Conclusions on the specific topic
engram conclusion search "topic" --observer <peer_id> --json

# Exercise the dialectic directly
engram peer chat <peer_id> "what do you know about X?" --json
engram peer chat <peer_id> "what happened here?" --scope my-project --json
engram workspace chat "what themes show up across peers?" --json
```
