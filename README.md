<!-- markdownlint-disable MD033 -->
<div align="center">
  <a href="https://app.engram.dev" target="_blank">
    <img src="assets/engram.svg" alt="Engram" width="400">
  </a>
</div>
<!-- markdownlint-enable MD033 -->

---

![Static Badge](https://img.shields.io/badge/Server-3.4.0-blue)
[![PyPI version](https://img.shields.io/pypi/v/engram-ai.svg)](https://pypi.org/project/engram-ai/)
[![NPM version](https://img.shields.io/npm/v/@engram-ai/sdk.svg)](https://npmjs.org/package/@engram-ai/sdk)
[![CLI](https://img.shields.io/pypi/v/engram-cli.svg?label=engram-cli)](https://pypi.org/project/engram-cli/)
[![Discord](https://img.shields.io/discord/1016845111637839922?style=flat&logo=discord&logoColor=23ffffff&label=Plastic%20Labs&labelColor=235865F2)](https://discord.gg/engram)

**Engram is memory infrastructure for building stateful agents that understand changing people, agents, groups, projects, and ideas over time.**

Store messages and events, let Engram reason in the background, then query peer representations, session context, search results, or natural-language insights from any model or framework. Use it managed at [api.engram.dev](https://api.engram.dev), run a local stack with [`engram start`](#cli), or self-host the FastAPI server yourself.

Using Engram as your memory system will earn your agents higher retention, more trust, and help you build data moats to out-compete incumbents.

> Engram has defined the Pareto Frontier of Agent Memory. Watch the [video](https://x.com/engramdotdev/status/2002090546521911703?s=20), check out our [evals page](https://engram.dev/evals/), and read the [blog post](https://blog.plasticlabs.ai/research/Benchmarking-Engram) for more detail.

## Contents

- [Start Here](#start-here)
- [Why Engram](#why-engram)
- [The Engram Loop](#the-engram-loop)
- [Quickstart](#quickstart)
- [What Engram Gives You](#what-engram-gives-you)
- [Integrations](#integrations)
- [CLI](#cli)
- [Core Concepts](#core-concepts)
- [Benchmarks & Evals](#benchmarks--evals)
- [Self-hosting](#self-hosting)
- [Configuration](#configuration)
- [Architecture](#architecture)
- [SDKs](#sdks)
- [Learn More](#learn-more)
- [Contributing](#contributing)
- [License](#license)

The Engram project is split between several repositories, with this one hosting the core service logic — implemented as a FastAPI server. Client SDKs for Python and TypeScript live in the [`sdks/`](./sdks) directory. The [`engram-cli`](./engram-cli) package lives here too.

## Start Here

| I want to...                           | Path                                                       | Get started                   |
| -------------------------------------- | ---------------------------------------------------------- | ----------------------------- |
| Give my coding agent persistent memory | Claude Code, Cursor, Grok Bot, OpenCode, Kilo Code, OpenClaw, Hermes, or any MCP client | [Integrations](#integrations) |
| Add memory to my product               | Python or TypeScript SDK                                   | [Quickstart](#quickstart)     |
| Run Engram locally                     | Install CLI, then `engram start --setup`                   | [CLI](#cli)                   |
| Inspect a deployment                   | `engram workspace inspect`, `engram doctor`                | [CLI](#cli)                   |
| Self-host from source                  | Docker Compose or local development                        | [Self-hosting](#self-hosting) |

## Why Engram

| Capability              | What it means                                                                        |
| ----------------------- | ------------------------------------------------------------------------------------ |
| Reasoning-first memory  | Extracts conclusions from conversations and events, not just matching chunks.        |
| Peer-centric model      | Tracks users, agents, groups, projects, and ideas as entities that change over time. |
| Multi-peer perspective  | Models what one peer knows about another when configured.                            |
| Managed or self-hosted  | Use `api.engram.dev`, `engram start` locally, or run the FastAPI server yourself.    |
| Agent-tool integrations | MCP, Claude Code, Cursor, Grok Bot, OpenCode, Kilo Code, OpenClaw, Hermes.  |

## The Engram Loop

1. **Store** conversations, events, documents, or tool traces as messages on a session.
2. **Reason** — Engram processes the queue in the background and updates peer representations.
3. **Query** — ask Engram for context, search results, peer representations, or a natural-language answer.
4. **Inject** — drop the result into any LLM call or agent framework.

Concretely: workspaces hold peers, peers participate in sessions, messages live on sessions, and Engram builds a per-peer representation that you query through the [Chat Endpoint](https://engram.dev/docs/v3/documentation/features/chat) or directly.

## Quickstart

Get an API key at [app.engram.dev](https://app.engram.dev) — when you sign up you'll be prompted to join an organization, which gets its own dedicated Engram instance. Or install the CLI and run [`engram start --setup`](#cli), then point the SDK at `http://localhost:8000`.

### Python

```bash
pip install engram-ai
# or: uv add engram-ai
# or: poetry add engram-ai
```

```python
import os
from engram import Engram

# Managed service uses api.engram.dev by default. For self-hosted, pass
# base_url="http://localhost:8000" or set ENGRAM_URL.
engram = Engram(
    workspace_id="my-app-testing",
    api_key=os.environ["ENGRAM_API_KEY"],
)

# 1. Store: peers and messages on a session
alice = engram.peer("alice")
tutor = engram.peer("tutor")
session = engram.session("session-1")
session.add_messages([
    alice.message("Hey there — can you help me with my math homework?"),
    tutor.message("Absolutely. Send me your first problem!"),
])

# 2. Reason: happens asynchronously in the background.

# 3. Query: ask Engram what it knows, or pull prompt-ready context.
answer = alice.chat("What learning styles does the user respond to best?")
context = session.context(summary=True, tokens=10_000)

# 4. Inject: hand the context to your model of choice.
from openai import OpenAI
client = OpenAI()
completion = client.chat.completions.create(
    model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
    messages=context.to_openai(assistant=tutor),
)
```

### TypeScript

```bash
npm install @engram-ai/sdk
# or: bun add @engram-ai/sdk
```

```typescript
import { Engram } from "@engram-ai/sdk";
import OpenAI from "openai";

const engram = new Engram({
  workspaceId: "my-app-testing",
  apiKey: process.env.ENGRAM_API_KEY,
});

const alice = await engram.peer("alice");
const tutor = await engram.peer("tutor");
const session = await engram.session("session-1");
await session.addMessages([
  alice.message("Hey there — can you help me with my math homework?"),
  tutor.message("Absolutely. Send me your first problem!"),
]);

const answer = await alice.chat(
  "What learning styles does the user respond to best?",
);
const context = await session.context({ summary: true, tokens: 10_000 });

const openai = new OpenAI();
const completion = await openai.chat.completions.create({
  model: process.env.OPENAI_MODEL ?? "gpt-4o-mini",
  messages: context.toOpenAI({ assistant: tutor }),
});
```

> **Note:** background reasoning is asynchronous. Newly-added messages may take a moment to be reflected in chat/representation responses; for low-latency reads, use the [`representation`](https://engram.dev/docs/v3/documentation/features/representation) endpoint.

## What Engram Gives You

| Need                               | API                                                             |
| ---------------------------------- | --------------------------------------------------------------- |
| Save interaction history           | `session.add_messages(...)`                                     |
| Ask what Engram knows about a peer | `peer.chat(...)`                                                |
| Ask across the whole workspace     | `engram.chat(...)` / `engram.chat_stream(...)`                  |
| Get prompt-ready context           | `session.context(...).to_openai(...)` / `.to_anthropic(...)`    |
| Hybrid search (BM25 + vector)      | `peer.search(...)`, `session.search(...)`, `engram.search(...)` |
| Low-latency static representations | `peer.representation(...)`, `session.representation(...)`       |
| Import documents                   | `session.upload_file(...)`                                      |
| Inspect background processing      | `engram.queue_status(...)`                                      |

See the full [SDK Reference](https://engram.dev/docs/v3/documentation/reference/sdk) and [API Reference](https://engram.dev/docs/v3/api-reference/introduction).

## Integrations

Engram ships a first-party memory plugin for every major coding agent. They all read the same
`~/.engram/config.json`, so one key configures all of them — and pointing two at the same `workspace`
gives them one shared memory.

| Agent            | Install                                                 | Source                                                             |
| ---------------- | ------------------------------------------------------- | ------------------------------------------------------------------ |
| Claude Code      | `/plugin marketplace add plastic-labs/claude-engram`    | [claude-engram](https://github.com/plastic-labs/claude-engram)     |
| Codex            | `npm install -g @engram-ai/codex-engram`                | [codex-engram](https://github.com/plastic-labs/codex-engram)       |
| Cursor           | Install **Engram** from the Cursor Marketplace          | [integrations/cursor](integrations/cursor/)                        |
| Grok Bot         | **Add to Grok Bot** from the Engram plugin page         | [integrations/cursor](integrations/cursor/)                        |
| DeepSeek Harness | `dsh plugin --profile <name> add @engram-ai/dsh-engram` | [dsh-engram](https://github.com/plastic-labs/dsh-engram)           |
| OpenCode         | `opencode plugin "@engram-ai/opencode-engram" --global` | [opencode-engram](https://github.com/plastic-labs/opencode-engram) |
| Kilo Code        | `kilo plugin @engram-ai/kilo-engram --global`           | [kilo-engram](kilo-engram/)                                        |
| OpenClaw         | `openclaw plugins install @engram-ai/openclaw-engram`   | [openclaw-engram](https://github.com/plastic-labs/openclaw-engram) |
| Hermes           | `hermes memory setup`                                   | built in upstream                                                  |
| Any MCP client   | `claude mcp add engram --transport http ...`            | [MCP guide](https://engram.dev/docs/v3/guides/integrations/mcp)    |

Get a key at [app.engram.dev](https://app.engram.dev), then `engram init` (or `uv tool install engram-cli && engram init`) writes it to `~/.engram/config.json` once for every integration. Cursor and Grok Bot are the exception: the marketplace plugin signs in with OAuth, and `engram init` is optional there (in Cursor it turns on automatic capture).

### Claude Code

Two ways, depending on how deep you want to go:

**Plugin (richer integration — recommended for Claude Code users):**

```text
/plugin marketplace add plastic-labs/claude-engram
/plugin install engram@engram
```

**Raw MCP (works in any MCP client — Cursor, Cline, Windsurf, etc.):**

```bash
claude mcp add engram \
  --transport http \
  --url "https://mcp.engram.dev" \
  --header "Authorization: Bearer hch-your-key-here" \
  --header "X-Engram-User-Name: YourName"
```

Details: [Claude Code guide](https://engram.dev/docs/v3/guides/integrations/claude-code) · [MCP guide](https://engram.dev/docs/v3/guides/integrations/mcp) · [repo](https://github.com/plastic-labs/claude-engram).

### Codex

```bash
npm install -g @engram-ai/codex-engram
codex-engram install      # registers hooks + MCP + skill in ~/.codex
```

Restart Codex to load the hooks. Details: [Codex guide](https://engram.dev/docs/v3/guides/integrations/codex) · [repo](https://github.com/plastic-labs/codex-engram).

### Cursor and Grok Bot

One Cursor Marketplace listing serves both. In Cursor, open **Customize**, install **Engram**, authenticate the `engram` MCP server, then run `/engram-setup` once. In Grok Bot, add **Engram** under **Connect apps** (or **Add to Grok Bot** from the plugin page) and ask a Bot to set up Engram. The plugin connects to the hosted MCP server over OAuth and ships the skills that drive the memory loop, so nothing runs locally.
Details: [Cursor guide](https://engram.dev/docs/v3/guides/integrations/cursor) · [Grok Bot guide](https://engram.dev/docs/v3/guides/integrations/grok-bot) · [source](integrations/cursor/).

### DeepSeek Harness

```bash
dsh plugin --profile <name> add @engram-ai/dsh-engram
```

A native Cordis plugin. It injects memory into the system prompt and captures new information from the session event feed. The model gets three tools — engram_search, engram_chat, and engram_remember — and you can run /engram to check status.
Details: [DeepSeek Harness guide](https://engram.dev/docs/v3/guides/integrations/deepseek-harness) · [repo](https://github.com/plastic-labs/dsh-engram).

### OpenCode

```bash
opencode plugin "@engram-ai/opencode-engram" --global
```

Details: [OpenCode guide](https://engram.dev/docs/v3/guides/integrations/opencode) · [repo](https://github.com/plastic-labs/opencode-engram).

### Kilo Code

```bash
kilo plugin @engram-ai/kilo-engram --global
```

One install covers the Kilo CLI, the VS Code extension, and the JetBrains plugin, since all three run the same Kilo server.
Details: [Kilo Code guide](https://engram.dev/docs/v3/guides/integrations/kilo) · [source](kilo-engram/).

### OpenClaw

```bash
openclaw plugins install @engram-ai/openclaw-engram
openclaw engram setup
openclaw gateway --force
```

`openclaw engram setup` prompts for your API key, writes the config, and optionally migrates legacy `MEMORY.md` / `USER.md` / `IDENTITY.md` files into Engram (non-destructive — originals are never deleted). Details: [OpenClaw guide](https://engram.dev/docs/v3/guides/integrations/openclaw) · [repo](https://github.com/plastic-labs/openclaw-engram).

### Hermes

```bash
hermes memory setup   # select "engram", point at api.engram.dev or your local server
```

Details: [Hermes guide](https://engram.dev/docs/v3/guides/integrations/hermes).

### Add Engram to your own codebase (agent skill)

For wiring the Engram SDK into an existing application, install the integration skill — it explores your codebase, asks about integration preferences, generates the SDK setup, and verifies it works:

```bash
npx skills add plastic-labs/engram
```

Then invoke `/engram-integration` in Claude Code (or `/engram-dev:integrate` via the plugin marketplace). The same command also installs the memory skills — `engram-memory` (concepts: the recall/record loop, session and peer strategy, plus how to connect and drive an MCP-connected Engram) and `engram-cli` (inspecting a deployment, or running a local stack with `engram start`). Details: [agentic development guide](https://engram.dev/docs/v3/documentation/introduction/vibecoding).

### Other MCP clients

The same `claude mcp add` form (or its client-specific equivalent) works in any MCP-compatible client. See [MCP guide](https://engram.dev/docs/v3/guides/integrations/mcp).

## CLI

[`engram-cli`](https://pypi.org/project/engram-cli/) inspects a Engram deployment from the terminal, or runs a personal local stack with Docker.

```bash
uv tool install engram-cli
engram init                 # Engram API key or browser login + server URL
engram start --setup basic  # local stack: LLM provider key + Docker
engram doctor
```

`engram init` authenticates the CLI against a Engram server. `engram start --setup` is a separate step: it writes the LLM provider key the local deriver needs and starts API + deriver + Postgres + Redis.

Full commands and local-stack details: [CLI reference](https://engram.dev/docs/v3/documentation/reference/cli) · [`engram-cli/README.md`](./engram-cli/README.md). To develop the server from source, see [Self-hosting](#self-hosting).

## Core Concepts

Engram organises everything around **peers** — humans and AI agents alike are first-class entities. The peer model enables:

- Multi-participant sessions with mixed human and AI agents
- Configurable observation settings (which peers observe which others)
- Flexible identity management for all participants
- Support for complex multi-agent interactions

Peers exchange messages within sessions; Engram reasons over those messages to build a representation of each peer that you can query.

- **Workspace** (formerly App): top-level container; isolates data between use cases.
- **Peer** (formerly User): any participant — human user or AI agent.
- **Session**: a conversation context; many-to-many with peers.
- **Scope**: a named grouping of sessions that bounds recall (chat, representation, search) to those members.
- **Message**: an atomic data unit (peer-to-peer communication or ingested document chunk).

What you query out of Engram:

- **Conclusions** — what Engram has extracted about a peer (deductive and inductive). Exposed via the [conclusions API](https://engram.dev/docs/v3/api-reference/introduction).
- **Representations** — static, low-latency snapshots of what Engram knows about a peer (optionally session-scoped).
- **Peer Cards** — compact identity summaries.
- **Session context / summaries** — prompt-ready bundles for long-running conversations.

<!-- markdownlint-disable MD033 -->
<details>
<summary>Internal storage (Collections &amp; Documents)</summary>

Internally, Engram stores peer-related observations in **collections** of vector-embedded **documents**. Collections are keyed by `(observer, observed)` peer pairs — the same mechanism powers self-representation (`observer == observed`) and cross-peer modelling (peer X's understanding of peer Y). These primitives are not exposed directly; the Conclusions API is the public surface.

</details>
<!-- markdownlint-enable MD033 -->

<!-- TODO(vineeth/marketing): write the "Engram vs RAG / vector DB / memory-only" comparison.
     Audit recommendation referenced; copy intentionally deferred to avoid inventing
     positioning claims unsupported by primary sources. -->

## Benchmarks &amp; Evals

Engram's evals span LongMemEval, LoCoMo, and other long-conversation benchmarks. See the [evals page](https://engram.dev/evals/), the [research blog post](https://blog.plasticlabs.ai/research/Benchmarking-Engram), and the [Pareto-frontier announcement video](https://x.com/engramdotdev/status/2002090546521911703?s=20) for methodology and reproducible results.

## Self-hosting

Engram is open source under AGPL-3.0. To **run** a personal instance, install the CLI (`uv tool install engram-cli`) and then [`engram start --setup`](#cli). The paths below are for building from source, contributing, or deploying without the CLI.

### Quick start (from source, Docker)

```bash
git clone https://github.com/plastic-labs/engram.git
cd engram
cp docker-compose.yml.example docker-compose.yml
cp .env.template .env       # set LLM_OPENAI_API_KEY (see "LLM provider" below for OpenRouter etc.)
docker compose up
```

Then point the SDKs at it:

```python
engram = Engram(workspace_id="my-app-testing", base_url="http://localhost:8000")
# or: export ENGRAM_URL=http://localhost:8000
```

<!-- markdownlint-disable MD033 -->
<details>
<summary>Without Docker (manual setup)</summary>

Everything below runs directly on the host — no Docker required. You need:

- [uv](https://docs.astral.sh/uv/) (it installs the required Python, 3.13+, for you)
- PostgreSQL with the [pgvector](https://github.com/pgvector/pgvector) extension, local or managed
- An API key for one LLM provider

Redis is optional; caching is off by default (`CACHE_ENABLED=false`).

1. **Clone and install**

```bash
git clone https://github.com/plastic-labs/engram.git
cd engram
uv sync
```

2. **Set up PostgreSQL with pgvector**

Install Postgres and pgvector natively, then create a `engram` role and database and enable the extensions in it as a superuser.

On Ubuntu/Debian:

```bash
# Postgres and pgvector majors must match the distro's packaged version.
# Ubuntu 24.04:
sudo apt install postgresql-16 postgresql-16-pgvector
# Debian 12:
sudo apt install postgresql-15 postgresql-15-pgvector
# Other versions: add the PostgreSQL APT repo (apt.postgresql.org) first.

sudo -u postgres psql -c "CREATE ROLE engram LOGIN PASSWORD 'engram';"
sudo -u postgres createdb -O engram engram
sudo -u postgres psql -d engram -c "CREATE EXTENSION IF NOT EXISTS vector;"
sudo -u postgres psql -d engram -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"  # optional, speeds up message search
```

On macOS, Homebrew makes your login user the superuser, so drop the `sudo -u postgres`:

```bash
brew install postgresql@17 pgvector
brew services start postgresql@17

psql -d postgres -c "CREATE ROLE engram LOGIN PASSWORD 'engram';"
createdb -O engram engram
psql -d engram -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -d engram -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
```

A managed Postgres that offers pgvector (Supabase, Neon, RDS, and so on) works too. Enable the same extensions in its database.

3. **Configure `.env`**

```bash
cp .env.template .env
```

Only two settings are required:

```env
DB_CONNECTION_URI=postgresql+psycopg://engram:engram@localhost:5432/engram
LLM_OPENAI_API_KEY=sk-...
```

`DB_CONNECTION_URI` must use the `postgresql+psycopg` prefix (a SQLAlchemy requirement).

**LLM provider.** You need one key, not one per vendor. Every feature defaults to `openai / gpt-5.4-mini`, and embeddings default to `openai / text-embedding-3-small`. To use OpenRouter or another OpenAI-compatible endpoint (Together, Fireworks, vLLM, Ollama, LiteLLM), put that provider's key in `LLM_OPENAI_API_KEY` and set the model and base URL on each feature in `.env`:

```env
LLM_OPENAI_API_KEY=sk-or-v1-...
DERIVER_MODEL_CONFIG__MODEL=google/gemini-2.5-flash
DERIVER_MODEL_CONFIG__OVERRIDES__BASE_URL=https://openrouter.ai/api/v1
# ...repeat for DIALECTIC_LEVELS__*, SUMMARY_*, DREAM_*
```

Models must support tool calling. If your provider doesn't serve embeddings, point `EMBEDDING_MODEL_CONFIG__*` at one that does. See [`.env.template`](./.env.template) for every per-feature line, and the [configuration guide](https://engram.dev/docs/v3/contributing/configuration#llm-configuration) for direct Anthropic/Gemini keys and mixing providers.

**Auth.** Auth is off by default (`AUTH_USE_AUTH=false`). Turn it on before exposing the server to a network. Enabling it requires a JWT secret, which you can generate with:

```bash
python scripts/generate_jwt_secret.py
```

This will generate a JWT secret and print it to the console. You can then set
the `AUTH_JWT_SECRET` environment variable. This is required for `AUTH_USE_AUTH`:

```env
AUTH_JWT_SECRET=<generated_secret>
```

Once auth is enabled, use `scripts/generate_jwt.py` to mint tokens for local
development and scripting:

```bash
# Admin token (full access, no expiry)
uv run python scripts/generate_jwt.py --admin

# Admin token expiring in 24 hours
uv run python scripts/generate_jwt.py --admin --expires 24h

# Workspace-scoped token
uv run python scripts/generate_jwt.py --workspace my-workspace --expires 30d

# Capture a token for use in curl/scripts
TOKEN=$(uv run python scripts/generate_jwt.py --admin --print-only)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/v3/workspaces
```

Duration units: `s` (seconds), `m` (minutes), `h` (hours), `d` (days), `w` (weeks), `y` (years).

4. **Run database migrations**

```bash
uv run alembic upgrade head
```

Migrations hold a session-level advisory lock, so they need a session-mode connection (direct Postgres or a session pooler), not a transaction-mode pooler. A Supabase-style `:6543` port is rewritten to `:5432` automatically.

5. **Launch Engram**

Two processes need to run alongside the database.

**Start the API server:**

```bash
uv run fastapi dev src/main.py                  # local development, reloads on code changes
uv run fastapi run --host 0.0.0.0 src/main.py   # on a server
```

**Start a background worker (deriver):**

In a separate terminal, run:

```bash
uv run python -m src.deriver
```

The deriver generates representations, summaries, peer cards, and manages dreaming tasks. You can increase the number of derivers to improve runtime efficiency.

For verification steps and production notes, see [Self-hosting docs → Manual Setup](https://engram.dev/docs/v3/contributing/self-hosting#manual-setup).

</details>
<!-- markdownlint-enable MD033 -->

Contributors: see [`CONTRIBUTING.md`](./CONTRIBUTING.md) for pre-commit setup. Deploying to Fly.io: see [Self-hosting docs → Deploying on Fly.io](https://engram.dev/docs/v3/contributing/self-hosting#deploying-on-fly-io).

## Configuration

Engram uses a flexible configuration system that supports both TOML files and environment variables. Configuration values are loaded in priority order: **environment variables > `.env` file > `config.toml` > defaults**.

Copy the example file to get started:

```bash
cp config.toml.example config.toml
```

The file is organized by subsystem — `[app]`, `[db]`, `[auth]`, `[cache]`, `[llm]`, `[deriver]`, `[dialectic]`, `[summary]`, `[dream]`, `[peer_card]`, `[webhook]`, `[metrics]`, `[telemetry]`, `[vector_store]`, and `[sentry]`. Any value can be overridden by an environment variable named `{SECTION}_{KEY}`, using `__` for nesting (`DIALECTIC_LEVELS__low__MODEL_CONFIG__MODEL`), or just `{KEY}` for app-level settings.

See the [configuration reference](https://engram.dev/docs/v3/contributing/configuration) for every available option, and [`.env.template`](./.env.template) for an annotated list of environment variables.

## Architecture

Engram splits into two services: **Storage** (workspaces, peers, sessions, scopes, messages, internal collections) and **Insights** (reasoning, conclusions, representations, summaries, the chat endpoint). Storage is synchronous via the API; Insights is asynchronous via a background queue consumed by the deriver worker process.

**Key features:**

- **Rich Reasoning System** — multiple implementation methods that extract conclusions from interactions and build comprehensive representations of peers
- **Chat Endpoint** — reasoning-informed responses that integrate conclusions with current context
- **Background Processing** — asynchronous processing pipeline for expensive operations like representation updates and session summarization
- **Multi-Provider Support** — configurable LLM providers for different use cases

<!-- markdownlint-disable MD033 MD001 -->
<details>
<summary>Storage primitives in detail</summary>

Engram contains several different primitives used for storing application and
peer data. This data is used for managing conversations, modeling peer
identity, building RAG applications, and more.

The philosophy behind Engram is to provide a platform that is peer-centric and
easily scalable from a single user to a million.

Below is a mapping of the different primitives and their relationships.

```
Workspaces
├── Peers ←──────────────────┐
│   ├── Sessions             │
│   └── (internal collections, keyed by observer/observed peer pair)
│                            │
├── Scopes ←─────────────────┤ (many-to-many with sessions)
│                            │
└── Sessions ←───────────────┤ (many-to-many with peers)
    ├── Peers ───────────────┘
    └── Messages (session-level)
```

**Relationship Details:**

- A **Workspace** contains multiple **Peers** and **Scopes**.
- **Peers** and **Sessions** have a many-to-many relationship (peers can participate in multiple sessions, sessions can have multiple peers).
- **Scopes** and **Sessions** have a many-to-many relationship (a session can belong to several scopes; a scope groups many sessions).
- **Messages** belong to a session and are labelled by their source peer.
- **Internal collections** of vector-embedded **documents** are keyed by `(observer, observed)` peer pairs. They are not directly exposed via the API; the observations stored in them are exposed as **Conclusions**.

Users familiar with APIs such as the OpenAI Assistants API will be familiar with
much of the mapping here.

#### Workspaces

This is the top level construct of Engram. Developers can register different
`Workspaces` for different assistants, agents, AI enabled features, etc. It is a way to
isolate data between use cases and provide multi-tenant capabilities.

#### Peers

Within a `Workspace` everything revolves around a `Peer`. The `Peer` object
represents any participant in the system — whether human users or AI agents.
This unified model enables complex multi-participant interactions.

#### Sessions

The `Session` object represents a set of interactions between `Peers` within a
`Workspace`. Other applications may refer to this as a thread or conversation.
Sessions can involve multiple peers with configurable observation settings.
A session can optionally join one or more **Scopes** at creation, or later via
the scopes API.

#### Scopes

A `Scope` is a named grouping of sessions inside a `Workspace`. It is a
visibility boundary on recall: chat, representation, session context, and
workspace search answered through a scope see only what happened in that
scope's member sessions. The underlying peers keep their unified
representations across everything they have participated in.

Developers manage scopes through the scopes API (`engram.scope(...)` /
`engram.scopes()`) and an optional `scopes` field on session create — not
through observer/observed configuration. Adding a session that already has
messages copies its existing explicit conclusions into the scope (no
re-derivation); removing one reconciles those copies back out. Query
backfill progress with the scope `status` endpoint.

A single scope name answers from that scope's collection and card. A list of
scopes restricts recall to the union of their member sessions. Empty scopes
fail closed. `scope` is mutually exclusive with `session` / `filters` on the
same read.

#### Messages

The `Message` represents an atomic data unit that exists at the session level:
communication between peers within a session context. All messages are labelled
by their source peer and can be processed asynchronously to update their
representations. This flexible design allows for both conversational interactions
and broader data ingestion for personality modelling.

</details>
<!-- markdownlint-enable MD033 MD001 -->

<!-- markdownlint-disable MD033 -->
<details>
<summary>Reasoning pipeline</summary>

The reasoning functionality of Engram is built on top of the Storage service. As
`Messages` and `Sessions` are created for `Peers`, Engram will asynchronously
reason about peer psychology to derive facts about them and store them
in reserved internal collections.

A high level summary of the pipeline is as follows:

1. Messages are created via the API.
2. Derivation tasks are enqueued for background processing, including:
   - `representation`: update representations of `Peers`.
   - `summary`: create summaries of `Sessions`.
3. Session-based queue processing ensures proper ordering.
4. Results are stored internally and surfaced via the Conclusions API, Representations, Peer Cards, and the Chat Endpoint.

</details>
<!-- markdownlint-enable MD033 -->

<!-- markdownlint-disable MD033 MD001 -->
<details>
<summary>Retrieving data and insights</summary>

Engram exposes several different ways to retrieve data from the system to best
serve the needs of any given application.

#### Get Context

In long-running conversations with an LLM, the context window can fill up
quickly. To address this, Engram provides a `context`
endpoint that returns a combination of messages, conclusions, summaries from a
session up to a provided token limit.

Use this to keep sessions going indefinitely. If you'd like to see this in action, try out [Engram Chat](https://engram.chat).

#### Search

There are several search endpoints that let developers query messages at the
`Workspace`, `Session`, or `Peer` level using a hybrid search strategy.

Requests can include advanced filters to further refine
the results.

#### Chat API

The flagship interface for using these insights is the [Chat Endpoint](https://engram.dev/docs/v3/documentation/features/chat) (`POST /peers/{peer_id}/chat`). It takes natural-language requests to get data about a peer and returns reasoning-grounded responses. Examples:

- Asking Engram for a generic or specific insight about the peer.
- Asking Engram to hydrate a prompt with data about the peer's behaviour.
- Asking Engram for a second opinion on how to respond.
- Getting personalised responses that incorporate long-term facts and context.

#### Representations

For low-latency use cases, Engram provides access to a `representation` endpoint that returns a static document with insights about a peer in the context of a particular session. Use this to quickly add context to a prompt without having to wait for an LLM response.

</details>
<!-- markdownlint-enable MD033 MD001 -->

## SDKs

- **Python** — [`engram-ai`](https://pypi.org/project/engram-ai/) on PyPI · source in [`sdks/python/`](./sdks/python)
- **TypeScript** — [`@engram-ai/sdk`](https://www.npmjs.com/package/@engram-ai/sdk) on npm · source in [`sdks/typescript/`](./sdks/typescript)
- **CLI** — [`engram-cli`](https://pypi.org/project/engram-cli/) on PyPI · source in [`engram-cli/`](./engram-cli) · [CLI reference](https://engram.dev/docs/v3/documentation/reference/cli)

SDKs are versioned independently of the server. Current SDK versions track each other; the server badge above reflects the deployed server version.

See the [SDK Reference](https://engram.dev/docs/v3/documentation/reference/sdk) for full API surface, the [API Reference](https://engram.dev/docs/v3/api-reference/introduction) for the raw HTTP API, and per-SDK example folders for runnable demos.

## Learn More

- [Developer documentation](https://engram.dev/docs/) — full API surface, guides, integrations.
- [CLI reference](https://engram.dev/docs/v3/documentation/reference/cli) — local stack, inspect/debug commands, scripting.
- [Plastic Labs blog](https://blog.plasticlabs.ai/) — design philosophy and history of the project.

## Contributing

We welcome contributions to Engram. One thing to know before you start: **pull requests must be linked to an issue carrying the `maintainer-approved` label**, or they are closed automatically. [Browse the approved queue](https://github.com/plastic-labs/engram/issues?q=is%3Aissue+is%3Aopen+label%3Amaintainer-approved), or make your case in [Discord](http://discord.gg/engram) — that is where maintainers are most active.

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the full process, an architecture walkthrough, and a map of where to change what. For vulnerabilities, see [SECURITY.md](./SECURITY.md) — note that Engram does not operate a bug bounty.

## License

Engram is licensed under the AGPL-3.0 License. Learn more at the [License file](./LICENSE).
