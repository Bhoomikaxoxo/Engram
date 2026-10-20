# Core Integration Patterns

The base SDK boilerplate for any Engram integration: choosing sync vs async, initializing the client, creating peers, configuring sessions, and adding messages. Read this once you've chosen your entities and session structure (Phases 1–2). For the agent-facing recall patterns (tool call, pre-fetch, `context()`), see `agent-patterns.md`.

## Sync vs Async

**TypeScript** — The SDK is async by default. All methods return promises. No separate sync API.

**Python** — The SDK provides both sync and async interfaces:

- **Sync** (default): `from engram import Engram` — use in sync frameworks (Flask, Django, CLI scripts)
- **Async**: `from engram import Engram` with `.aio` namespace — use in async frameworks (FastAPI, Starlette, async workers)

```python
# Sync usage (Flask, Django, scripts)
from engram import Engram
engram = Engram(workspace_id="my-app", api_key=os.environ["ENGRAM_API_KEY"])
peer = engram.peer("user-123")
response = peer.chat("What does this user prefer?")

# Async usage (FastAPI, Starlette)
from engram import Engram
engram = Engram(workspace_id="my-app", api_key=os.environ["ENGRAM_API_KEY"])
peer = await engram.aio.peer("user-123")
response = await peer.aio.chat("What does this user prefer?")
```

Match the client to the framework — check whether the codebase uses `async def` handlers or sync `def` handlers and choose accordingly. The examples below show sync Python; swap to `.aio` equivalents for async codebases.

## 1. Initialize with a Single Workspace

Use ONE workspace for your entire application. The workspace name should reflect your app/product.

**Python:**

```python
from engram import Engram
import os

# Sync client (Flask, Django, scripts)
engram = Engram(
    workspace_id="your-app-name",
    api_key=os.environ["ENGRAM_API_KEY"],
    environment="production"
)

# Async client (FastAPI, Starlette) — use engram.aio for all operations
# engram.aio.peer(), engram.aio.session(), etc.
```

**TypeScript:**

```typescript
import { Engram } from '@engram-ai/sdk';

// All methods are async by default
const engram = new Engram({
    workspaceId: "your-app-name",
    apiKey: process.env.ENGRAM_API_KEY,
    environment: "production"
});
```

## 2. Create Peers for ALL Entities

Create peers for **every entity** in your business logic - users AND AI assistants.

**Python:**

```python
from engram.api_types import PeerConfig

# Human users (observed by default)
user = engram.peer("user-123")

# AI assistants can be observed too — leave observe_me on (the default) if you
# want a model of the assistant.
assistant = engram.peer("assistant")

# Deterministic bots (scripted/rule-based) - set observe_me=False; there's
# nothing meaningful for Engram to model.
notification_bot = engram.peer("notification-bot", configuration=PeerConfig(observe_me=False))
```

**TypeScript:**

```typescript
// Human users (observed by default)
const user = await engram.peer("user-123");

// AI assistants can be observed too — leave observeMe on (the default) if you
// want a model of the assistant.
const assistant = await engram.peer("assistant");

// Deterministic bots (scripted/rule-based) - set observeMe=false; there's
// nothing meaningful for Engram to model.
const notificationBot = await engram.peer("notification-bot", { configuration: { observeMe: false } });
```

## 3. Multi-Peer Sessions

Sessions can have multiple participants. Configure observation settings per-peer.

**Python:**

```python
from engram.api_types import SessionPeerConfig

session = engram.session("conversation-123")

# User is observed (Engram builds a model of them)
user_config = SessionPeerConfig(observe_me=True, observe_others=True)

# A deterministic bot is NOT observed (no model built of it). An AI assistant
# could stay observed instead — observe_me defaults to True.
bot_config = SessionPeerConfig(observe_me=False, observe_others=True)

session.add_peers([
    (user, user_config),
    (notification_bot, bot_config)
])
```

**TypeScript:**

```typescript
const session = await engram.session("conversation-123");

await session.addPeers([
    // A deterministic bot isn't observed; an AI assistant could stay observed
    // instead (observeMe defaults to true).
    [user, { observeMe: true, observeOthers: true }],
    [notificationBot, { observeMe: false, observeOthers: true }]
]);
```

## 4. Add Messages to Sessions

**Python:**

```python
session.add_messages([
    user.message("I'm having trouble with my account"),
    assistant.message("I'd be happy to help. What seems to be the issue?"),
    user.message("I can't reset my password")
])
```

**TypeScript:**

```typescript
await session.addMessages([
    user.message("I'm having trouble with my account"),
    assistant.message("I'd be happy to help. What seems to be the issue?"),
    user.message("I can't reset my password")
]);
```
