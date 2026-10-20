import { expect, test } from "bun:test"
import os from "node:os"
import path from "node:path"
import { mkdtemp } from "node:fs/promises"

import { __testing, createEngramRuntimePlugin, ENGRAM_COMMAND } from "../dist/index.js"

const { touchesEngramFiles } = __testing
const home = os.homedir()
const defaultConfig = path.join(home, ".engram", "config.json")
const project = path.join(home, "code", "app")

const createPluginHarness = async (rootDir, configPath) =>
  createEngramRuntimePlugin({ configPath })({
    client: { app: { log: async () => undefined } },
    project: { id: "kilo", worktree: rootDir },
    directory: rootDir,
    worktree: rootDir,
    serverUrl: new URL("http://127.0.0.1:4096"),
    $: {},
  })

test("the guard catches the ways an agent names ~/.engram", () => {
  const blocked = [
    { command: "cat ~/.engram/config.json" },
    { command: "cat $HOME/.ENGRAM/config.json | jq .apiKey" },
    { command: "ls -la ~/.engram*" },
    { command: "cd ~ && cat .engram/config.json" },
    { command: "cat config.json", workdir: path.join(home, ".engram") },
    { filePath: defaultConfig },
    { filePath: "../../.engram/config.json" },
    { path: "~/.engram" },
    { pattern: "**/.engram/**" },
    { patchText: "*** Begin Patch\n*** Update File: ~/.engram/config.json\n@@\n-a\n+b\n*** End Patch" },
  ]
  for (const args of blocked) expect([args, touchesEngramFiles(args, defaultConfig, project)]).toEqual([args, true])
})

test("the guard leaves ordinary project work alone", () => {
  const allowed = [
    { command: "bun test && grep -rn engram src" },
    { command: "npx @engram-ai/kilo-engram --help" },
    { command: "cat kilo-engram/README.md" },
    { filePath: path.join(project, "src", ".engramrc") },
    { filePath: path.join(project, "docs", "setup.md"), content: "Kilo saves the key to ~/.engram/config.json." },
    { pattern: "engram", path: project },
    { patchText: "*** Begin Patch\n*** Update File: docs/setup.md\n@@\n-old\n+See ~/.engram/config.json\n*** End Patch" },
    "not an object",
  ]
  for (const args of allowed) expect([args, touchesEngramFiles(args, defaultConfig, project)]).toEqual([args, false])
})

test("with KILO_ENGRAM_CONFIG_PATH the guard covers that file and its activity folder", () => {
  const configPath = path.join(home, "test", "engram-config.json")
  const activityFile = path.join(home, "test", "kilo", "sessions", "ses_1.json")
  expect(touchesEngramFiles({ filePath: configPath }, configPath, project)).toBe(true)
  expect(touchesEngramFiles({ filePath: "engram-config.json" }, configPath, path.join(home, "test"))).toBe(true)
  expect(touchesEngramFiles({ command: "cat ~/test/engram-config.json" }, configPath, project)).toBe(true)
  expect(touchesEngramFiles({ filePath: activityFile }, configPath, project)).toBe(true)
  expect(touchesEngramFiles({ filePath: path.join(home, "test", "notes.md") }, configPath, project)).toBe(false)
})

test("tool.execute.before refuses a tool call that reads the Engram config and points the agent to engram_status", async () => {
  const rootDir = await mkdtemp(path.join(os.tmpdir(), "engram-guard-root-"))
  const hooks = await createPluginHarness(rootDir)
  const input = { tool: "read", sessionID: "ses_guard", callID: "call_1" }
  await expect(hooks["tool.execute.before"](input, { args: { filePath: defaultConfig } })).rejects.toThrow("engram_status")
  await expect(hooks["tool.execute.before"](input, { args: { filePath: path.join(rootDir, "a.ts") } })).resolves.toBeUndefined()
  await expect(
    hooks["tool.execute.before"]({ ...input, tool: "engram_status" }, { args: { path: "~/.engram" } }),
  ).resolves.toBeUndefined()
})

test("the config hook adds /engram for the desktop app and IDE extensions without replacing a user's own", async () => {
  const rootDir = await mkdtemp(path.join(os.tmpdir(), "engram-command-root-"))
  const hooks = await createPluginHarness(rootDir)
  const config = {}
  await hooks.config(config)
  expect(config.command.engram).toEqual(ENGRAM_COMMAND)
  expect(config.command.engram.template).toContain("engram_status")
  expect(config.command.engram.template).toContain("engram_setup")
  expect(config.command.engram.template).toContain("$ARGUMENTS")
  expect(config.command.engram.template).not.toContain("npx")

  const custom = { command: { engram: { template: "my own" }, other: { template: "x" } } }
  await hooks.config(custom)
  expect(custom.command.engram.template).toBe("my own")
  expect(custom.command.other.template).toBe("x")
})
