---
name: engram-integration
description: Integrate Engram memory into existing Python or TypeScript codebases. Use when adding Engram SDK, setting up peers, configuring sessions, and accessing Engram's representation.
allowed-tools: Read, Glob, Grep, Bash(uv:*), Bash(bun:*), Bash(npm:*), Edit, Write, WebFetch, AskUserQuestion
---

# Engram Integration Guide

## What is Engram

Engram is an open source memory library for building stateful agents. It works with any model, framework, or architecture. You send Engram the messages from your conversations, and custom reasoning models process them in the background — extracting premises, drawing conclusions, and building rich representations of each participant over time. Your agent can then query those representations on-demand ("What does this user care about?", "How technical is this person?") and get grounded, reasoned answers.

The key mental model: **Peers** are any participant — human or AI. Both are represented the same way. `observe_me` is a peer-level flag (`PeerConfig`) controlling whether Engram forms a representation of *that* peer; typically you want Engram to model your users (`observe_me=True`) but not anything with deterministic behavior (`observe_me=False`). `observe_others` is a separate per-peer `SessionPeerConfig` setting that controls whether that peer forms representations of the *other* participants in a session. **Sessions** scope conversations between peers. **Messages** are the raw data you feed in — Engram reasons about them asynchronously and stores the results as the peer's **representation**. No messages means no reasoning means no memory.

Your agent accesses this memory through `peer.chat(query)` (ask a natural language question, get a reasoned answer — a few seconds of live reasoning) or `session.context()` (near-instant read of formatted history + representation). Prefer `context()` for per-turn grounding; use `chat()` when you need a reasoned answer.

## Reference map

Follow the workflow below. Read a reference file only when you reach the step that needs it:

| When you're… | Read |
| --- | --- |
| Writing the client/peer/session setup (init, peers, sessions, add messages) | `references/core-patterns.md` |
| Wiring how the AI reads context (tool call, pre-fetch, `context()`, streaming) | `references/agent-patterns.md` |
| Integrating into a bot framework (nanobot, openclaw, picoclaw, …) | `references/bot-frameworks.md` + `references/bot-frameworks/<framework>/` |

## Integration Workflow

Follow these phases in order:

### Phase 1: Codebase Exploration

Before asking the user anything, explore the codebase to understand:

1. **Language & Framework**: Is this Python or TypeScript? What frameworks are used (FastAPI, Express, Next.js, etc.)?
2. **Existing AI/LLM code**: Search for existing LLM integrations (OpenAI, Anthropic, LangChain, etc.)
3. **Entity structure**: Identify users, agents, bots, or other entities that interact
4. **Session/conversation handling**: How does the app currently manage conversations?
5. **Message flow**: Where are messages sent/received? What's the request/response cycle?

Use Glob and Grep to find:

- `**/*.py` or `**/*.ts` files with "openai", "anthropic", "llm", "chat", "message"
- User/session models or types
- API routes handling chat or conversation endpoints

> **Bot framework detected?** If the codebase is built around an agent loop, tool registry, session manager, and message bus (e.g., nanobot, openclaw, picoclaw), read `references/bot-frameworks.md` for framework-specific integration guidance and check `references/bot-frameworks/<framework>/` for concrete reference implementations.

### Phase 2: Interview (REQUIRED)

After exploring the codebase, use the **AskUserQuestion** tool to clarify integration requirements. Ask these questions (adapt based on what you learned in Phase 1):

#### Question Set 1 - Entities & Peers

Ask about which entities should be Engram peers:

- header: "Peers"
- question: "Which entities should Engram track and build representations for?"
- options based on what you found (e.g., "End users only", "Users + AI assistant", "Users + multiple AI agents", "All participants including third-party services")
- Include a follow-up if they have multiple AI agents: should any AI peers be observed?

#### Question Set 2 - Integration Pattern

Ask how they want to use Engram context (see `references/agent-patterns.md` for the implementation of each):

- header: "Pattern"
- question: "How should your AI access Engram's user context?"
- options:
  - "Tool call (Recommended)" - "Agent queries Engram on-demand via function calling"
  - "Pre-fetch" - "Fetch user context before each LLM call with predefined queries"
  - "context()" - "Include conversation history and representations in prompt"
  - "Multiple patterns" - "Combine approaches for different use cases"

#### Question Set 3 - Session Structure

Ask about conversation structure:

- header: "Sessions"
- question: "How should conversations map to Engram sessions?"
- options based on their app (e.g., "One session per chat thread", "One session per user", "Multiple users per session (group chat)", "Custom session logic")

#### Question Set 4 - Specific Queries (if using pre-fetch pattern)

If they chose pre-fetch, ask what context matters:

- header: "Context"
- question: "What user context should be fetched for the AI?"
- multiSelect: true
- options: "Communication style", "Expertise level", "Goals/priorities", "Preferences", "Recent activity summary", "Custom queries"

### Phase 3: Implementation

Based on interview responses, implement the integration:

1. Install the SDK (see [Installation](#installation))
2. Create Engram client initialization — `references/core-patterns.md` §1
3. Set up peer creation for identified entities — `references/core-patterns.md` §2–3
4. Implement the chosen integration pattern(s) — `references/agent-patterns.md`
5. Add message storage after exchanges — `references/core-patterns.md` §4
6. Update any existing conversation handlers

### Phase 4: Verification

- If the Engram CLI is available, run `engram doctor` to confirm connectivity before testing the integration code
- Use `engram peer list` and `engram peer chat` to verify peers exist and the dialectic endpoint works independently of the integration
- Ensure all message exchanges are stored to Engram
- Verify deterministic bot peers have `observe_me=False`; AI-assistant peers can keep observation on (it's fine to model them)
- Check that the workspace ID is consistent across the codebase
- Confirm environment variable for API key is documented

---

## Before You Start

1. **Check the latest SDK versions** at <https://engram.dev/docs/changelog/introduction.md>
   - Python SDK: `engram-ai`
   - TypeScript SDK: `@engram-ai/sdk`

2. **Get an API key** ask the user to get a Engram API key from <https://app.engram.dev> and add it to the environment.

3. **Verify with the CLI** (optional but recommended). If the user has the Engram CLI installed (`uv install engram-cli`), they can validate their setup before writing any integration code:

   ```bash
   engram init          # persist API key + URL to ~/.engram/config.json
   engram doctor        # verify connectivity, config, workspace health
   engram peer chat     # test the dialectic endpoint interactively
   ```

   This is the fastest way to confirm the API key and URL are correct before debugging SDK code.

## Installation

### Python (use uv)

```bash
uv add engram-ai
```

### TypeScript (use bun)

```bash
bun add @engram-ai/sdk
```

The SDK is sync-by-default in Python (with an `.aio` async namespace) and async-only in TypeScript — match the client to your framework. Full sync/async guidance and the base client/peer/session/message code are in `references/core-patterns.md`.

## Integration Checklist

When integrating Engram into an existing codebase:

- [ ] Install SDK with `uv add engram-ai` (Python) or `bun add @engram-ai/sdk` (TypeScript)
- [ ] Set up `ENGRAM_API_KEY` environment variable
- [ ] Initialize Engram client with a single workspace ID
- [ ] Create peers for all entities (users AND AI assistants)
- [ ] Set `observe_me=False` for deterministic bot peers (optional for AI assistants — fine to leave observation on)
- [ ] Configure sessions with appropriate peer observation settings
- [ ] Choose integration pattern:
  - [ ] Tool call pattern for agentic systems
  - [ ] Pre-fetch pattern for simpler integrations
  - [ ] context() for conversation history
- [ ] Store messages after each exchange to build user models
- [ ] (Optional) Run `engram doctor` to verify connectivity before testing integration code
- [ ] (Optional) Use `engram peer chat` to test dialectic queries independently

## Common Mistakes to Avoid

1. **Multiple workspaces**: Use ONE workspace per application
2. **Forgetting AI peers**: Create peers for AI assistants, not just users
3. **Modeling bots**: Set `observe_me=False` for deterministic bots (scripted output — nothing meaningful to model). For AI assistants it's fine to leave observation on; turning it off is an optional optimization when you only care about the user.
4. **Not storing messages**: Always call `add_messages()` to feed Engram's reasoning engine
5. **Blocking on processing**: Messages are processed asynchronously — don't poll or wait for reasoning to complete before continuing

## Resources

- Documentation (LLM-friendly index): <https://engram.dev/docs/llms.txt>
- Latest SDK versions: <https://engram.dev/docs/changelog/introduction.md>
- API Reference: <https://engram.dev/docs/v3/api-reference/introduction.md>

> Tip: append `.md` to any Engram docs URL to fetch the raw Markdown version.
