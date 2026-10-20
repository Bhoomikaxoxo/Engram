---
name: engram-memory
description: Persistent cross-session memory via Engram — recall what you know about the user before working, and save durable insights after.
license: MIT
---

# Engram memory

You have a persistent memory of this user that survives across sessions, backed by Engram. In `hybrid` or `context` recall mode the Kilo plugin's hooks inject relevant context each turn; in `tools` mode this skill is how memory reaches you. The hooks record the conversation in every mode. This skill is for the times you should reach for memory *actively*.

## When to pull memory

Before non-trivial work, query memory instead of guessing:

- The task touches the user's preferences, conventions, or past decisions
- You're about to make an assumption you could instead verify ("which package manager?", "how is auth done here?")
- The user references something from "before" or "last time"

Use the Engram tools:

- `engram_search` — semantic lookup over the messages in this Engram session only; it does not reach other chats or sessions
- `engram_chat` — ask a natural-language question about the user or project ("what's their testing style?"); this is the tool for what Engram knows across sessions

## When to save memory

After you learn something durable, persist it with `engram_create_conclusion`:

- A decision with rationale ("chose SQLite over Postgres — embedded, zero-setup")
- A stable preference ("prefers small, focused PRs")
- A non-obvious gotcha or root cause worth remembering
- A convention specific to this codebase

Keep each conclusion to one concise statement with the *why*. Review before adding near-duplicates.

## When not to bother

Skip memory for throwaway or purely mechanical tasks — running a build, answering a general knowledge question, trivial edits. Don't narrate that you checked memory; just use it.

## Engram's own files

Never read, print or edit `~/.engram/config.json`, and never run Engram setup commands in a shell. The file holds the user's API key. Call `engram_status` to see Engram's settings, and `engram_setup` to set Engram up; it asks for the key in a window, never in chat. The user can also type `/engram`.
