# Engram Integration for Bot Frameworks

This reference extends the main engram-integration skill for **bot frameworks** — applications built around an agent loop, session manager, tool registry, and message bus (e.g., nanobot, openclaw, picoclaw).

## Supported Frameworks

When a known framework is detected, use concrete reference implementations from `{baseDir}/references/bot-frameworks/<framework>/`.

| Framework | Status | Reference Dir |
|-----------|--------|---------------|
| [nanobot](https://github.com/HKUDS/nanobot) | concrete references | `bot-frameworks/nanobot/` |
| openclaw | planned | -- |
| picoclaw | planned | -- |

For unknown frameworks, adapt the general pattern below to the codebase's architecture.

## Phase 1: Explore (bot-specific)

In addition to the main skill's Phase 1, identify these bot-specific components:

1. **Agent loop**: Where messages are processed (look for `while` loops calling an LLM)
2. **Session manager**: How conversation history is stored (JSONL files, database, in-memory)
3. **Tool registry**: How tools/functions are registered for the LLM to call
4. **Message bus**: How inbound/outbound messages are routed between channels and the agent
5. **Config system**: How the bot loads configuration (JSON, YAML, env vars, pydantic models, zod schemas)
6. **CLI entry points**: How the bot is started (commands, gateway, agent modes)

If the framework matches a known one (e.g., nanobot), pull the concrete references from `{baseDir}/references/bot-frameworks/<framework>/` and use them as the implementation target.

## Phase 2: Interview (bot-specific)

In addition to the main skill's interview questions, ask about:

- **Peer model**: Who are the participants? (typically: one user peer per channel:chat_id, one shared assistant peer)
- **Session granularity**: One session per chat? Per user? Per channel?
- **Workspace ID**: What namespace for this bot's Engram data?
- **Feature flag**: Should Engram be opt-in (default `false`) or opt-out (default `true`)?

## Phase 3: Implement (bot-specific)

### Step 1: Add dependency

**Python:** Add `engram-ai>=2.0.1`. If the framework supports optional dependencies, make it optional:

```toml
[project.optional-dependencies]
engram = ["engram-ai>=2.0.1"]
```

**TypeScript:** Add `@engram-ai/sdk`:

```bash
bun add @engram-ai/sdk
# or npm install @engram-ai/sdk
```

If the framework supports optional peer dependencies:

```json
{
  "peerDependencies": {
    "@engram-ai/sdk": ">=2.0.1"
  },
  "peerDependenciesMeta": {
    "@engram-ai/sdk": { "optional": true }
  }
}
```

### Step 2: Add config schema

Add a Engram config section to the bot's configuration system:

**Python:**

```python
class EngramConfig(BaseModel):
    """Engram AI-native memory integration (optional feature flag)."""
    enabled: bool = False  # or True for Engram-first deployments
    workspace_id: str = "default"
    prefetch: bool = True  # inject user context into system prompts
    context_tokens: int | None = None
    environment: str = "production"
```

**TypeScript:**

```typescript
interface EngramConfig {
  /** Engram AI-native memory integration (optional feature flag). */
  enabled: boolean;        // default: false, or true for Engram-first deployments
  workspaceId: string;     // default: "default"
  prefetch: boolean;       // default: true — inject user context into system prompts
  contextTokens?: number;
  environment: string;     // default: "production"
}

const defaultEngramConfig: EngramConfig = {
  enabled: false,
  workspaceId: "default",
  prefetch: true,
  environment: "production",
};
```

### Step 3: Create the engram package

Create a engram integration package with:

- **Client singleton** (`client.py` / `client.ts`): Lazy initialization, deferred imports, `getEngramClient()` factory
- **Session manager** (`session.py` / `session.ts`): Maps bot sessions to Engram sessions with peer configuration
- **Agent tool** (`engram_tool.py` / `engramTool.ts`): Tool the agent can call to query user context via `peer.chat()`

Key patterns (Python):

- `from __future__ import annotations` + `TYPE_CHECKING` for all engram imports
- Runtime imports inside functions (never top-level) so the bot doesn't crash without `engram-ai`
- Wrap in `try/except ImportError` for graceful degradation

Key patterns (TypeScript):

- Use dynamic `import()` for engram SDK (never top-level `import ... from`) so the bot doesn't crash without `@engram-ai/sdk`
- Use `import type { ... }` for type-only imports that are erased at runtime
- Wrap in `try/catch` for graceful degradation when the SDK is missing

Key patterns (shared):

- IDs sanitized to `^[a-zA-Z0-9_-]+` (Engram requirement)
- User peer: `observe_me=True, observe_others=True`
- Assistant/bot peer: `observe_others=True`; set `observe_me=False` only for deterministic bots (scripted output — nothing to model). AI-assistant bots can keep `observe_me=True`.

If references exist for this framework, use them directly from `{baseDir}/references/bot-frameworks/<framework>/`.

### Step 4: Wire into the agent loop

Add these integration points to the agent loop:

1. **Tool registration** (at startup): If `engram.enabled` and `ENGRAM_API_KEY` set, initialize client + register Engram tools.

   **Python:** Wrap in `try/except ImportError` for graceful degradation.
   **TypeScript:** Use dynamic `import()` inside a `try/catch` block.

2. **Context setup** (per message): Set session context on Engram tools, ensure Engram session exists.

3. **Prefetch** (per message): Call `session.context()` to get user representation and inject into system prompt before the LLM call.

4. **Sync** (after response): After saving to local session, sync the user+assistant message pair to Engram.

   **Python:**

   ```python
   session.add_messages([
       user_peer.message(user_input),
       assistant_peer.message(assistant_response),
   ])
   ```

   **TypeScript:**

   ```typescript
   await session.addMessages([
       userPeer.message(userInput),
       assistantPeer.message(assistantResponse),
   ]);
   ```

5. **Migration** (on first activation): If Engram session is empty but local session has history, upload prior messages as a file via `session.upload_file()` (Python) or `session.uploadFile()` (TypeScript). Also upload `MEMORY.md` and `HISTORY.md` if they exist (from frameworks with local memory consolidation). Archive originals after successful upload.

### Step 5: Pass config through CLI

Pass `engram_config` to every agent loop instantiation in the CLI commands.

### Step 6: Migration support

When Engram activates on an instance with existing local data, migrate automatically:

- **Session messages** (JSONL files): Format as XML transcript, upload via `session.upload_file()` (Python) or `session.uploadFile()` (TypeScript)
- **Consolidated memory** (MEMORY.md, HISTORY.md): Upload as tagged files with context annotations
- **Archive originals**: Move to `migrated/` subdirectory after successful upload
- **Idempotent**: Skip if Engram session already has messages

## Phase 4: Verify (bot-specific)

After integration, verify:

- [ ] Bot starts normally without the Engram SDK installed (no import errors)
- [ ] Bot starts normally with the SDK but without `ENGRAM_API_KEY` (graceful skip)
- [ ] With both present and `enabled=true`, logs show "Engram tools registered"
- [ ] User context is prefetched and visible in system prompts
- [ ] Messages sync to Engram after each exchange
- [ ] Local session migration works on first Engram activation
- [ ] Memory file migration works for MEMORY.md/HISTORY.md (if applicable)

## Bot-Specific Patterns

- **Lazy imports everywhere**:
  - Python: `from __future__ import annotations` + `TYPE_CHECKING` for type hints, runtime imports inside functions
  - TypeScript: `import type { ... }` for type-only imports, dynamic `import()` for runtime access
- **Feature flag gating**: Always check `config.enabled` AND `ENGRAM_API_KEY` / `process.env.ENGRAM_API_KEY` before touching Engram
- **Graceful degradation**:
  - Python: `try/except ImportError` and generic `Exception` catches with logger warnings, never crash the bot
  - TypeScript: `try/catch` around dynamic `import()` with logger warnings, never crash the bot
- **Sanitize IDs**: Engram requires `^[a-zA-Z0-9_-]+` — replace colons, dots, spaces with dashes
- **Sync after success**: Only mark messages as synced after the API call succeeds, not before
- **Cache consistency**: When creating aliased sessions, store under both original and derived keys
