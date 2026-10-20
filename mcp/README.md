# Engram MCP Server

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server for [Engram](https://engram.dev). The hosted path is a Cloudflare Worker; the same tools also run over stdio and over Streamable HTTP (`bun src/http.ts`) for Docker and other long-lived process hosts.

## Quickstart: Use the Hosted Server

1. Get an API key at <https://app.engram.dev>
2. Add Engram to your Claude Desktop config:

```json
{
  "mcpServers": {
    "engram": {
      "command": "bunx",
      "args": [
        "mcp-remote",
        "https://mcp.engram.dev",
        "--header",
        "Authorization:${AUTH_HEADER}"
      ],
      "env": {
        "AUTH_HEADER": "Bearer <your-engram-key>"
      }
    }
  }
}
```

Every workspace-scoped tool takes a `workspace_id` argument. If you set `X-Engram-Workspace-ID` on the connection, that value fills `workspace_id` when the argument is omitted. Use `list_workspaces` to discover IDs.

## Naming your client

Set `X-Engram-Plugin` on the connection to name whatever configured it: `<name>/<version>` for an integration (`cursor-engram/0.2.0`), or a short slug for a hand-written config (`cursor`). Without it, the server records the caller's `User-Agent`. Optional; nothing changes without it.

## Available Tools

**Workspace:** `list_workspaces` (id, metadata, created_at), `create_workspace` (get-or-create with optional metadata), `inspect_workspace` (aggregates metadata, configuration, and peer/session IDs), `search` (semantic search scoped by optional peer/session/scope params), `workspace_chat` (reasoned answer across all peers; optional session / scope recall bounds), `get_metadata`, `set_metadata`

**Peers:** `create_peer`, `list_peers`, `chat` (reasoned answer about one peer; optional session / scope / sessions recall bounds), `get_peer_card`, `set_peer_card`, `get_peer_context`, `get_representation` (optional session / scope / sessions recall bounds)

**Sessions:** `create_session` (optional `scopes` to join at creation), `list_sessions`, `delete_session`, `clone_session`, `add_peers_to_session`, `remove_peers_from_session`, `get_session_peers`, `inspect_session`, `add_messages_to_session`, `get_session_messages`, `get_session_message`, `get_session_context` (optional `peer_target` with `peer_perspective` / `scope` / `limit_to_session` to include a peer's representation and card)

**Scopes:** `list_scopes`, `get_scope_sessions`, `create_scope` (get-or-create with optional metadata), `add_sessions_to_scope`, `remove_session_from_scope`, `get_scope_status` (backfill progress per session)

**Conclusions:** `list_conclusions`, `query_conclusions`, `create_conclusions`, `delete_conclusion`

**System:** `schedule_dream`, `get_queue_status`

## Architecture

```
src/
  index.ts              # Worker entry point — parse config, delegate to MCP handler
  stdio.ts              # Local stdio host (bun src/stdio.ts)
  http.ts               # Streamable HTTP host (bun src/http.ts / Docker)
  server.ts             # createServer() — registers all tools on an McpServer
  config.ts             # EngramConfig, parseConfig(), Engram clients + X-Engram-* headers
  types.ts              # ToolContext, result helpers
  tools/
    workspace.ts        # inspect, list, search, workspace_chat, metadata
    peers.ts            # CRUD, chat (session / scope / sessions recall bounds), card, context, representation
    scopes.ts           # list/create scopes, scope membership, backfill status
    sessions.ts         # CRUD, peers, messages, inspect, context, clone
    conclusions.ts      # list, query, create, delete
    system.ts           # dream, queue status
```

Built on:

- **[agents](https://www.npmjs.com/package/agents)** — `createMcpHandler` for Cloudflare Workers
- **[@modelcontextprotocol/sdk](https://www.npmjs.com/package/@modelcontextprotocol/sdk)** — `McpServer` for tool registration
- **[@engram-ai/sdk](https://www.npmjs.com/package/@engram-ai/sdk)** v2 — Engram TypeScript SDK

## Self-Hosted Engram

If you run Engram yourself, point this server at it with `ENGRAM_API_URL`.
When unset, requests go to `https://api.engram.dev`.

`ENGRAM_TIMEOUT_MS` caps each Engram API request (default 300000, 5 minutes).
Raise it if `chat` runs longer than that on your model. A reverse proxy in
front of the HTTP host needs a read timeout at least this long.

**Cloudflare Worker (`bun run dev` / `bun run deploy`):** create `mcp/.dev.vars`:

```
ENGRAM_API_URL=http://127.0.0.1:28000
```

For a deployed Worker: `wrangler secret put ENGRAM_API_URL`.

To report errors to Sentry, set `SENTRY_DSN` the same way
(`wrangler secret put SENTRY_DSN`). The HTTP and stdio hosts read `SENTRY_DSN`
from the environment. Without it, error reporting is a no-op on every host.

## HTTP host

For Docker or any platform that runs a long-lived process, use the Streamable
HTTP entry instead of the Worker. Clients keep the same `mcp-remote` shape as
`https://mcp.engram.dev`. Sessions live in process memory — run one instance.

```bash
cd mcp && bun install
ENGRAM_API_URL=http://127.0.0.1:8000 bun run http
```

```bash
bunx mcp-remote http://127.0.0.1:3000 \
  --header "Authorization:Bearer <key>"
```

Auth is the `Authorization: Bearer` header (same as the Worker). Established
sessions still require that same bearer. Optional `X-Engram-Workspace-ID`
fills `workspace_id` when the tool argument is omitted, and optional
`X-Engram-Plugin` names the caller (see [Naming your client](#naming-your-client)).

`HOST` defaults to `0.0.0.0`, `PORT` to `3000`. `GET /health` is unauthenticated.
MCP is served at `/` and `/mcp`. Idle sessions expire after
`MCP_SESSION_IDLE_MS` (default 30 minutes); `MCP_SESSION_MAX` (default 128)
caps concurrent sessions.

A platform start command is `bun src/http.ts` (or `bun run http` from `mcp/`).
This repo does not ship a `vercel.json`; serverless replicas do not share the
in-memory session map.

### Docker

```bash
docker build -f mcp/Dockerfile -t engram-mcp mcp
docker run --rm -p 3000:3000 \
  -e ENGRAM_API_URL=http://host.docker.internal:8000 \
  engram-mcp
```

`docker-compose.yml.example` includes an `mcp` service beside `api` and
`deriver` (`ENGRAM_API_URL=http://api:8000`, port `127.0.0.1:3000`).

## Local stdio

For a local Engram instance, or any MCP client that spawns a process, run the
stdio host. `--cwd` loads `mcp/bunfig.toml` (Markdown loader) from this package.

```bash
cd mcp && bun install

claude mcp add engram \
  -e ENGRAM_API_KEY=hch-your-key-here \
  -e ENGRAM_API_URL=http://127.0.0.1:28000 \
  -e ENGRAM_WORKSPACE_ID=my-workspace \
  -- bun --cwd "$(pwd)" src/stdio.ts
```

`ENGRAM_API_URL` defaults to `https://api.engram.dev`. `ENGRAM_WORKSPACE_ID` is
optional; without it, pass `workspace_id` on each tool call.

## Development

### Setup

```bash
bun install
```

### Local dev

```bash
bun dev
```

### Type-check

```bash
bun run tsc --noEmit
```

### Test locally

Worker (`bun dev`, port 8787) or HTTP host (`bun run http`, port 3000):

```bash
bunx mcp-remote http://localhost:8787 \
  --header "Authorization:Bearer <key>"
```

### Deploy

```bash
bun run deploy              # production
bun run deploy:staging      # staging
```
