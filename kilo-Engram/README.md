# Engram Plugin for Kilo Code

> Add AI-native memory to Kilo Code

This plugin gives Kilo Code long-term memory that survives context wipes, session restarts and fresh chats. Engram remembers what you work on, your durable preferences and prior context across projects. The plugin runs inside `kilo serve`, so it works in the Kilo CLI, the VS Code extension and the JetBrains plugin.

## Quick Start

### Step 1: Get Your Engram API Key

1. Go to **[app.engram.dev](https://app.engram.dev)**
2. Sign up or log in
3. Copy your API key

### Step 2: Install the Plugin

```bash
kilo plugin @engram-ai/kilo-engram --global
```

`kilo plugin` installs the package and adds it to the `plugin` list of Kilo's global config (the server half) and `~/.config/kilo/tui.json` (the `/engram:*` commands). It still uses Kilo's older `opencode.json` name for the server entry; Kilo reads `kilo.jsonc`, `kilo.json` and `opencode.json` alike. To update an existing install, add `--force`. To add it by hand, put `"@engram-ai/kilo-engram"` in the `plugin` array of `~/.config/kilo/kilo.jsonc` and `~/.config/kilo/tui.json`.

For the Kilo desktop app or the VS Code and JetBrains extensions, install **Engram** from the Kilo Marketplace, then type `/engram` in the chat. The agent asks what name Engram should call you and opens a window on your screen for your API key. You can skip Step 3.

Until Engram is listed in the Kilo Marketplace, add `"@engram-ai/kilo-engram"` to the `plugin` array of `~/.config/kilo/kilo.jsonc` yourself, creating the file if it does not exist. Restart Kilo, then type `/engram`.

### Step 3: Run Setup in Kilo

1. Start Kilo. The first time the plugin loads without an API key, it offers to set up Engram.
2. Choose **Set up now**, or run `/engram:setup`
3. Keep the default `Engram Cloud` option unless you want a self-hosted or local endpoint
4. Enter your Engram API key
5. Confirm the name Engram should call you. Setup fills in the `peerName` your other Engram tools use, or your OS user name.
6. Choose a workspace: Kilo's own, or one another Engram tool already uses
7. Run `/engram:status` to check the runtime

## What You Get

- **Persistent memory.** Kilo keeps durable context across sessions.
- **Hook-driven recall.** Hooks add memory to the prompt and record significant tool activity, so recall works with any model.
- **Engram memory skill.** A `engram-memory` skill is installed into Kilo's skills directory, so the agent knows when to pull and save memory on its own.
- **Cloud or local.** Use Engram Cloud, or point at a self-hosted or local Engram instance.
- **Session mapping.** Sessions can be scoped per directory, repo, branch, chat instance or globally.
- **Peer modeling.** User and agent observation are configurable (`observationMode`, `agentObserveMe`).
- **Visible recall.** A Engram section in Kilo's sidebar shows what Engram added to the session, and `/engram:recall` shows the exact text.

## Configuration

Configuration lives in the shared file `~/.engram/config.json`, which other Engram plugins also read. Kilo-specific settings live under `hosts.kilo`.

```jsonc
{
  "apiKey": "hch-...",
  "peerName": "user",
  "baseUrl": "https://api.engram.dev",
  "hosts": {
    "kilo": {
      "workspace": "kilo",
      "aiPeer": "kilo",
      "recallMode": "hybrid",
      "observationMode": "unified",
      "agentObserveMe": false,
      "autoConclusions": false,
      "sessionStrategy": "per-directory",
      "apiKey": "hch-..." // optional; overrides the root apiKey for Kilo
    }
  }
}
```

Set `KILO_ENGRAM_CONFIG_PATH` to read and write a different file.

### Cloud vs Local

For Engram Cloud, `apiKey` is required and `baseUrl` stays `https://api.engram.dev`.

For self-hosted or local Engram, point `baseUrl` at your deployment, for example `http://127.0.0.1:8000`. `apiKey` is needed only if that deployment requires authentication. If Kilo runs in Docker or on another machine, `localhost` may not be your machine; the `baseUrl` must be reachable from where `kilo serve` runs.

### Session Strategies

| Strategy | Behavior | Best for |
| --- | --- | --- |
| `per-directory` | One session per working directory | Default project memory |
| `per-repo` | One session per repository | Repos with several entry directories |
| `git-branch` | Session changes with the current branch | Branch-specific work |
| `per-session` | New session for each Kilo session id | Short-lived isolated work |
| `chat-instance` | Session follows the current chat instance | Very short-lived use |
| `global` | One session for everything | Shared memory across all work |

### Observation Mode

This decides which Engram collection `engram_chat`, `engram_create_conclusion` and per-prompt recall use for the user.

| Mode | Collection | Best for |
| --- | --- | --- |
| `unified` (default) | The user's own collection (`observer=user`, `observed=user`) | Several agents sharing what they learn about you |
| `directional` | This agent's view of the user (`observer=aiPeer`, `observed=user`) | Memory kept separate per agent |

In `unified` mode the agent peer does not observe the user, so Engram derives each message once. If you switch to `directional`, the agent's view of you starts from the messages saved after the switch.

### Peer name

Your peer is your `peerName`, unchanged, so Kilo uses the same peer as your other Engram tools. Kilo reads `ENGRAM_PEER_NAME`, then `peerName` in `~/.engram/config.json`, then your OS user name (`$USER`). Characters Engram does not allow in ids become `-`. The plugin writes `~/.engram/config.json` only when you run setup or change a setting.

A peer belongs to one workspace. Kilo uses its own `kilo` workspace by default, so it starts with no memory of you. To share memory with another Engram tool, choose that tool's workspace in `/engram:setup`, or set `hosts.kilo.workspace` to it. This changes nothing for the other tool.

`peerName` and `aiPeer` must differ. If they match, Engram calls fail with an error in the sidebar until you change one.

### Agent self-observation

The agent peer is created with `observeMe: false`, so Engram models you, not the assistant. Set `agentObserveMe: true` to give the agent its own representation.

### Auto conclusions

Engram derives conclusions from every saved message. With `autoConclusions: true`, the plugin also saves a prompt verbatim as a conclusion when it contains phrases such as "I prefer", "always", "never" or "remember that". The conclusion is available on the next prompt, before Engram's deriver runs. It is off by default because it also saves prompts like "never mind, revert that".

## Kilo CLI, Desktop App and IDE Extensions

Every Kilo client starts its own local Kilo server, and the plugin runs inside it. Recall, saving, the `engram_*` tools and the `/engram` command work in all of them. The sidebar section and the `/engram:*` commands come from the terminal UI half, which only the Kilo CLI loads.

| | Kilo CLI | Desktop app, VS Code, JetBrains |
| --- | --- | --- |
| Setup | `/engram:setup`, or **Set up now** on first load | `/engram`, or yes to the agent's offer |
| `/engram` | Yes | Yes |
| Engram sidebar section and `/engram:*` commands | Yes | No |
| Check that Engram is working | Sidebar, `/engram:status`, `/engram:recall` | `/engram` |

Outside the CLI:

- The desktop app and editors opened from the Dock or an app launcher do not see shell-profile variables such as `ENGRAM_API_KEY`. Save the key with setup.
- Each desktop chat runs in its own folder, so each chat is its own Engram session. Memory of you carries across chats; `engram_search` only searches the current session.
- The desktop app and the extensions bundle their own Kilo version, and read the same `~/.config/kilo` and `~/.engram/config.json` as the CLI.

## Seeing What Engram Did

Kilo's sidebar shows `Memory • Disabled` when Kilo's own memory feature is off. The plugin adds a Engram section directly below it:

```
Engram
• Active
Peer: alice
Session: View in Engram ↗
/engram:recall
```

On Engram Cloud, clicking `View in Engram` opens the session in the Engram dashboard, where you can read the saved messages and the conclusions. Any other Engram server has no known dashboard address, so the sidebar shows the session name, shortened in the middle to fit. Clicking `/engram:recall` opens the recall view. The section shows `Not set up` before `/engram:setup`, and `Error` with the reason when a Engram request fails.

`/engram:recall` opens the exact text the model received. Kilo does not save this text in its session history.

The server half writes this record to `~/.engram/kilo/sessions/<session id>.json` with mode 600, and the TUI reads it. The sidebar and the `/engram:*` commands belong to the Kilo CLI's terminal UI. The desktop app and the VS Code and JetBrains extensions do not load TUI plugins, so they show neither. When Engram has no API key, the agent offers setup once per session.

## Operator Commands

| Command | Description |
| --- | --- |
| `/engram` | Set up Engram from the chat, or show your peer, workspace, session link and latest recall. Every Kilo client lists it. |
| `/engram:setup` | First-time setup for cloud or local Engram |
| `/engram:status` | Effective Engram status for the current project |
| `/engram:recall` | The exact memory text Engram added to the current session |
| `/engram:settings` | Effective config values and config paths |
| `/engram:config` | Edit shared Engram fields in `~/.engram/config.json` |
| `/engram:import` | Preview or import local Kilo session history into Engram |

The `/engram:*` commands are part of the Kilo CLI only. `/engram` is a prompt to the agent, so it uses a model call.

`/engram:import` reads history through the Kilo SDK client, maps sessions with the same `sessionStrategy` as live capture, and uploads user and assistant text with the original timestamps. The first run is a dry run. Imported sessions are recorded in `~/.engram/kilo-import-state.json` and skipped next time.

## Agent Tools

| Tool | Description |
| --- | --- |
| `engram_setup` | Save the peer name and workspace, and ask for the API key in a window on the user's screen. A key never passes through the chat, and the saved key is never sent to a new server. |
| `engram_status` | Show effective runtime status |
| `engram_get_config` | Read effective and persisted settings |
| `engram_set_config` | Update a persisted shared setting. `apiKey` and `baseUrl` can only be changed by the user. |
| `engram_search` | Search the messages in the current Engram session only |
| `engram_chat` | Ask Engram a question answered by reasoning over memory |
| `engram_create_conclusion` | Save a durable fact about the user |

The agent cannot read Engram's config. The plugin refuses any Kilo tool call that names `~/.engram`, the config file in use, or the session activity folder, and tells the agent to call `engram_status` instead. It checks file paths and command text, so it stops an agent that means well, but not one that hides the path on purpose.

## Plugin Surfaces

| Purpose | Kilo hook |
| --- | --- |
| Record your prompt, fetch prompt-specific recall | `chat.message` |
| Attach recall to the request without saving it to Kilo's history | `experimental.chat.messages.transform` |
| Memory instructions and a stable snapshot | `experimental.chat.system.transform` |
| Continuity block during compaction | `experimental.session.compacting` |
| Refuse tool calls that name Engram's config | `tool.execute.before` |
| Record significant tool activity | `tool.execute.after` |
| `ENGRAM_URL` and `ENGRAM_WORKSPACE_ID` for shell tools (never the API key) | `shell.env` |
| `engram_*` tools | `tool` |
| The `/engram` command in every client | `config` |
| Session start, assistant capture, cleanup | `event` |
| Engram sidebar section (TUI) | `sidebar_content` slot |

The packaged `engram-memory` skill is copied to `~/.config/kilo/skills/engram-memory` (`$XDG_CONFIG_HOME/kilo/skills/engram-memory` when that is set), which every Kilo client reads.

## Remote and Headless Use

The plugin runs wherever Kilo's server runs, and reads `~/.engram/config.json` on that machine. When no window can open on your screen, finish setup on that machine in one of two ways:

- Run `/engram:setup` in the Kilo CLI there, if that machine has it.
- Write `~/.engram/config.json` yourself with at least `apiKey` and `peerName` (see [Configuration](#configuration)), then run `chmod 600 ~/.engram/config.json`.

- **VS Code Remote SSH, dev containers, Codespaces.** Kilo's server runs on the remote machine, so it reads the remote's `~/.engram/config.json`, not your laptop's. Set Engram up on the remote.
- **Key window over SSH.** On macOS and Windows, `engram_setup` does not open the key window in an SSH session, because it would appear on that machine's own screen. The agent tells you to finish setup one of the two ways above instead. On Linux it opens only when a display is available, including through X forwarding. An unanswered window closes after 2 minutes.
- **CI and scripts.** When the `CI` variable is set, the agent does not offer setup. Set `ENGRAM_API_KEY` to use Engram in CI, or `KILO_PURE=1` to turn off every plugin.

## Development

```bash
bun install
bun run check
bun run test
```

`bun run build` compiles the sidebar's JSX with `@opentui/solid`'s Bun plugin. `solid-js` and `@opentui/*` stay external: Kilo rewrites those imports to its own copies when it loads the plugin, so the sidebar shares Kilo's Solid runtime.

To load a local build in Kilo, build it and point the `plugin` array at the server entry by file path. The exported plugin id makes a file-path entry valid:

```jsonc
{
  "plugin": ["file:///absolute/path/to/kilo-engram/dist/server.js"]
}
```

Plugin logs appear in Kilo's log under `service=kilo-engram`; run `kilo run --print-logs` to see them on stderr.
