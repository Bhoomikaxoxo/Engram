# Engram TypeScript SDK

A high-level, ergonomic TypeScript SDK for the Engram conversational memory platform. Provides a user-friendly API for managing peers, sessions, and conversational context.

## Installation

```
npm install @engram-ai/sdk
```

## Usage

```ts
import { Engram } from "@engram-ai/sdk";

const engram = new Engram({
  apiKey: process.env.ENGRAM_API_KEY,
  baseURL: "http://localhost:8000",
  workspaceId: "test",
});

const assistant = await engram.peer("bob");
const alice = await engram.peer("alice");

await engram.peers();

const session = await engram.session("session_1");
await session.addPeers([alice, assistant]);

await session.addMessages([
  assistant.message("What did you have for breakfast today, alice?"),
  alice.message("I had oatmeal."),
]);

const response = await alice.chat("what did alice have for breakfast today?");
console.log(response);
```

See `examples/` for more.

## Development

### Type checking

```bash
bun run typecheck
```

### Testing

Tests for the SDK live in `tests/` at the monorepo root and are run via pytest, which orchestrates a test server. Do not run `bun test` directly.

```bash
# From the monorepo root
uv run pytest tests/ -k typescript
```
