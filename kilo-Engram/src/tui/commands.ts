import { readFile } from "node:fs/promises"
import { readActivity } from "../activity.js"
import { createEngramClient } from "../engram-client.js"
import { executeKiloImport, planKiloImport } from "../import.js"
import {
  DEFAULT_SETTINGS,
  HOST_ID,
  SETTING_ENUMS,
  getNestedValue,
  isLocalBaseUrl,
  isObservationMode,
  isRecord,
  peerCollisionError,
  resolveBaseUrl,
  resolvePeerName,
  resolveSessionPeerIds,
  sharedConfigPath,
  unifiedImportFollowUp,
  writeFileAtomic,
} from "../core.js"
import { recallMessage } from "./activity-view.js"
import type { DialogOption, GlobalSettings, TuiCommandSpec, TuiSession } from "./dialogs.js"

export const resolveConfigPath = () => sharedConfigPath(process.env.KILO_ENGRAM_CONFIG_PATH)

const SHARED_CONFIG_PRESETS: Record<string, readonly string[]> = Object.fromEntries(
  Object.entries(SETTING_ENUMS).map(([key, values]) => [key.toLowerCase(), values]),
)

const MODE_EDITABLE_FIELD_PATHS = [
  "apiKey",
  "baseUrl",
  "peerName",
  "hosts.kilo.workspace",
  "hosts.kilo.aiPeer",
  "hosts.kilo.recallMode",
  "hosts.kilo.observationMode",
  "hosts.kilo.agentObserveMe",
  "hosts.kilo.autoConclusions",
  "hosts.kilo.sessionStrategy",
] as const

export const readGlobalSettings = async (): Promise<GlobalSettings> => {
  const configPath = resolveConfigPath()
  try {
    const raw = await readFile(configPath, "utf-8")
    const parsed = JSON.parse(raw)
    return isRecord(parsed) ? (parsed as GlobalSettings) : {}
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") {
      return {}
    }
    throw error
  }
}

export const readSharedConfig = async (): Promise<Record<string, unknown> | null> => {
  const configPath = resolveConfigPath()
  try {
    const raw = await readFile(configPath, "utf-8")
    const parsed = JSON.parse(raw)
    if (!isRecord(parsed)) {
      throw new Error(`${configPath} must contain a JSON object at the top level.`)
    }
    return parsed
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") {
      return null
    }
    throw error
  }
}

// The file can hold an API key, so only its owner may read it. Other Engram tools read it too, so it is never half-written.
const writeConfigFile = async (configPath: string, settings: Record<string, unknown>) => {
  await writeFileAtomic(configPath, `${JSON.stringify(settings, null, 2)}\n`, 0o600)
  return configPath
}

export const writeSharedConfig = (settings: Record<string, unknown>) => writeConfigFile(resolveConfigPath(), settings)

const listSharedConfigFields = (value: Record<string, unknown>, prefix = ""): string[] =>
  Object.entries(value).flatMap(([key, entryValue]) => {
    const nextKey = prefix ? `${prefix}.${key}` : key
    if (isRecord(entryValue) && Object.keys(entryValue).length > 0) {
      return listSharedConfigFields(entryValue, nextKey)
    }
    return [nextKey]
  })

const setNestedValue = (value: Record<string, unknown>, fieldPath: string, nextValue: unknown) => {
  const parts = fieldPath.split(".")
  let current: Record<string, unknown> = value
  for (const part of parts.slice(0, -1)) {
    const existing = current[part]
    if (!isRecord(existing)) {
      current[part] = {}
    }
    current = current[part] as Record<string, unknown>
  }
  current[parts.at(-1) as string] = nextValue
}

export const resolveSharedConfigField = (config: Record<string, unknown>, field: string) => {
  const canonical = listSharedConfigFields(config).find(
    (candidate) => candidate.toLowerCase() === field.trim().toLowerCase(),
  )
  if (!canonical) {
    throw new Error(`Field '${field}' does not exist in ${resolveConfigPath()}.`)
  }
  return canonical
}

export const modeEditableFieldPaths = () => [...MODE_EDITABLE_FIELD_PATHS]

export const sharedConfigPresetOptions = (fieldPath: string, currentValue: unknown) => {
  const presetKey = fieldPath.split(".").at(-1)?.toLowerCase() || fieldPath.toLowerCase()
  if (SHARED_CONFIG_PRESETS[presetKey]) {
    return [...SHARED_CONFIG_PRESETS[presetKey]]
  }
  if (typeof currentValue === "boolean") {
    return ["true", "false"]
  }
  return []
}

const parseSharedConfigValue = (currentValue: unknown, rawValue: string) => {
  const trimmed = rawValue.trim()
  if (typeof currentValue === "boolean") {
    return trimmed.toLowerCase() === "true"
  }
  if (typeof currentValue === "number") {
    const parsed = Number(trimmed)
    if (!Number.isFinite(parsed)) {
      throw new Error(`Expected a number for this field, received '${rawValue}'.`)
    }
    return parsed
  }
  return trimmed
}

const writeGlobalSettings = (settings: GlobalSettings) => writeConfigFile(resolveConfigPath(), settings)

export const normalizeSettings = (settings: GlobalSettings) => ({
  baseUrl: resolveBaseUrl(settings as Record<string, unknown>) || DEFAULT_SETTINGS.baseUrl,
  apiKey: typeof settings.apiKey === "string" && settings.apiKey.trim() ? settings.apiKey.trim() : "",
  peerName: typeof settings.peerName === "string" ? settings.peerName.trim() : "",
})

export const validateCloudApiKey = (value: string) =>
  value.trim() ? null : "Engram Cloud requires a Engram API key. Enter a non-empty key or choose Self-hosted / local."

// The server lets ENGRAM_* env values win over the file, so status reports what the server uses.
// Display only: nothing here is ever written back to the config file.
const withEnvOverrides = (normalized: ReturnType<typeof normalizeSettings>) => ({
  baseUrl: process.env.ENGRAM_URL?.trim() || process.env.ENGRAM_BASE_URL?.trim() || normalized.baseUrl,
  apiKey: process.env.ENGRAM_API_KEY?.trim() || normalized.apiKey,
  peerName: process.env.ENGRAM_PEER_NAME?.trim() || normalized.peerName,
})

// What the server checks before it talks to Engram, including ENGRAM_* env values.
const configuredForServer = (settings: GlobalSettings) => {
  const normalized = withEnvOverrides(normalizeSettings(settings))
  return Boolean(normalized.apiKey) || isLocalBaseUrl(normalized.baseUrl)
}

export const statusMessage = (
  settings: GlobalSettings,
  liveStatus?: { workspaceName?: string; kiloSessionId?: string },
) => {
  const normalized = withEnvOverrides(normalizeSettings(settings))
  const configured = configuredForServer(settings)
  const deployment = isLocalBaseUrl(normalized.baseUrl)
    ? "Local / self-hosted"
    : normalized.baseUrl === DEFAULT_SETTINGS.baseUrl
      ? "Engram Cloud"
      : "Custom endpoint"
  return [
    `Configured: ${configured ? "yes" : "no"}`,
    `Deployment: ${deployment}`,
    `Base URL: ${normalized.baseUrl}`,
    `API key: ${normalized.apiKey ? "set" : "not set"}`,
    `Peer name: ${resolvePeerName(normalized.peerName)}`,
    ...(liveStatus?.workspaceName ? [`Workspace: ${liveStatus.workspaceName}`] : []),
    ...(liveStatus?.kiloSessionId ? [`Kilo session: ${liveStatus.kiloSessionId}`] : []),
    `Config path: ${resolveConfigPath()}`,
    "",
    configured ? "Engram is ready for Kilo." : "Run /engram:setup to finish configuration.",
  ].join("\n")
}

export const settingsMessage = (settings: GlobalSettings) => {
  const host = settings.hosts?.kilo || {}
  return [
    `Config path: ${resolveConfigPath()}`,
    `API key: ${settings.apiKey?.trim() ? "set" : "not set"}`,
    `Peer name: ${resolvePeerName(settings.peerName)}`,
    `Base URL: ${resolveBaseUrl(settings as Record<string, unknown>) || DEFAULT_SETTINGS.baseUrl}`,
    `Workspace: ${host.workspace || DEFAULT_SETTINGS.workspace}`,
    `AI peer: ${host.aiPeer || DEFAULT_SETTINGS.aiPeer}`,
    `Recall mode: ${host.recallMode || DEFAULT_SETTINGS.recallMode}`,
    `Observation mode: ${host.observationMode || DEFAULT_SETTINGS.observationMode}`,
    `Agent observe me: ${host.agentObserveMe === true ? "true" : "false"}`,
    `Auto conclusions: ${host.autoConclusions === true ? "true" : "false"}`,
    `Session strategy: ${host.sessionStrategy || DEFAULT_SETTINGS.sessionStrategy}`,
  ].join("\n")
}

const observationModeOptions = (): DialogOption<string>[] => [
  { title: "unified", value: "unified", description: "Your own memory, shared with other unified Engram tools" },
  { title: "directional", value: "directional", description: "This Kilo agent's own view of you" },
]

export const saveSettings = async (partial: Partial<GlobalSettings>) => {
  const current = await readGlobalSettings()
  const sharedRaw = (await readSharedConfig()) ?? {}
  const partialHost = partial.hosts?.kilo
  const nextApiKey =
    typeof partial.apiKey === "string"
      ? partial.apiKey
      : typeof current.apiKey === "string"
        ? current.apiKey
        : undefined
  const nextPeerName =
    typeof partial.peerName === "string" && partial.peerName.trim()
      ? partial.peerName.trim()
      : resolvePeerName(current.peerName)
  const currentHosts = isRecord(sharedRaw.hosts) ? { ...sharedRaw.hosts } : {}
  const currentHost = isRecord(currentHosts.kilo) ? currentHosts.kilo : {}
  currentHosts.kilo = {
    ...currentHost,
    workspace: partialHost?.workspace ?? current.hosts?.kilo?.workspace ?? DEFAULT_SETTINGS.workspace,
    aiPeer: partialHost?.aiPeer ?? current.hosts?.kilo?.aiPeer ?? DEFAULT_SETTINGS.aiPeer,
    recallMode: partialHost?.recallMode ?? current.hosts?.kilo?.recallMode ?? DEFAULT_SETTINGS.recallMode,
    sessionStrategy: partialHost?.sessionStrategy ?? current.hosts?.kilo?.sessionStrategy ?? DEFAULT_SETTINGS.sessionStrategy,
  }

  const next: GlobalSettings & Record<string, unknown> = {
    ...sharedRaw,
    baseUrl:
      typeof partial.baseUrl === "string"
        ? partial.baseUrl
        : typeof current.baseUrl === "string"
          ? current.baseUrl
          : DEFAULT_SETTINGS.baseUrl,
    peerName: nextPeerName,
    hosts: currentHosts,
  }
  if (typeof nextApiKey === "string") {
    next.apiKey = nextApiKey
  } else {
    delete next.apiKey
  }
  return writeGlobalSettings(next)
}

const importConfigFromSettings = (settings: GlobalSettings) => {
  const host = settings.hosts?.kilo || {}
  const workspaceId = (host.workspace || DEFAULT_SETTINGS.workspace).trim() || DEFAULT_SETTINGS.workspace
  const aiPeer = host.aiPeer || DEFAULT_SETTINGS.aiPeer
  const { userPeerId, agentPeerId } = resolveSessionPeerIds(resolvePeerName(settings.peerName), aiPeer)
  if (userPeerId === agentPeerId) throw new Error(peerCollisionError(userPeerId))
  return {
    apiKey: settings.apiKey || "",
    baseUrl: resolveBaseUrl(settings as Record<string, unknown>) || DEFAULT_SETTINGS.baseUrl,
    workspaceId,
    userPeerId,
    agentPeerId,
    sessionStrategy: host.sessionStrategy || DEFAULT_SETTINGS.sessionStrategy,
    agentObserveMe: host.agentObserveMe === true,
    observationMode: isObservationMode(host.observationMode) ? host.observationMode : DEFAULT_SETTINGS.observationMode,
  }
}

const formatImportPreview = (plan: Awaited<ReturnType<typeof planKiloImport>>) => {
  const lines = [
    `Source: ${plan.source}`,
    `Window: last ${plan.days} days`,
    `Ready to import: ${plan.sessionCount} session(s), ${plan.messageCount} message(s)`,
    `Already imported: ${plan.alreadyImportedCount}`,
    `Skipped empty: ${plan.skippedCount}`,
    "",
  ]
  for (const session of plan.sessions.filter((item) => !item.skippedReason).slice(0, 12)) {
    lines.push(`- ${session.title} (${session.messageCount} msg)`)
  }
  if (plan.sessionCount > 12) lines.push(`- … and ${plan.sessionCount - 12} more`)
  return lines.join("\n")
}

const isConfigured = (settings: GlobalSettings) =>
  Boolean(settings.apiKey?.trim()) || isLocalBaseUrl(resolveBaseUrl(settings as Record<string, unknown>))

/** Offered once when the plugin is installed or updated and Engram has no API key yet. */
export const offerSetup = async (session: TuiSession) => {
  try {
    if (configuredForServer(await readGlobalSettings())) return
    const choice = await session.dialogs.select<"setup" | "later">({
      title: "Engram is installed. Set up memory now?",
      options: [
        { title: "Set up now", value: "setup", description: "Paste a key from app.engram.dev" },
        { title: "Later", value: "later", description: "Run /engram:setup any time" },
      ],
    })
    if (choice === "setup") await runSetup(session)
  } catch {
    return
  }
}

export const runStatus = async (session: TuiSession) => {
  const settings = await readGlobalSettings()
  await session.dialogs.alert({
    title: "Engram Status",
    message: statusMessage(settings, session.liveStatus(settings)),
  })
}

export const runSettings = async (session: TuiSession) => {
  const settings = await readGlobalSettings()
  await session.dialogs.alert({ title: "Engram Settings", message: settingsMessage(settings) })
}

export const runConfig = async (session: TuiSession) => {
  let config: Record<string, unknown> | null
  try {
    config = await readSharedConfig()
  } catch (error) {
    await session.dialogs.alert({
      title: "Engram config invalid",
      message: error instanceof Error ? error.message : String(error),
    })
    return
  }
  if (!config) {
    await session.dialogs.alert({
      title: "Engram config missing",
      message: `The config does not exist at ${resolveConfigPath()}.`,
    })
    return
  }

  const fieldPath = await session.dialogs.select<string>({
    title: "Which field should be modified?",
    options: modeEditableFieldPaths().map((value) => ({ title: value, value })),
  })
  if (!fieldPath) return

  const currentValue = getNestedValue(config, fieldPath)
  const presetOptions = sharedConfigPresetOptions(fieldPath, currentValue)
  const rawValue =
    presetOptions.length > 0
      ? await session.dialogs.select<string>({
          title: fieldPath.endsWith("observationMode")
            ? "Engram observation mode"
            : `What should it be set to: ${presetOptions.join(", ")}`,
          options: fieldPath.endsWith("observationMode")
            ? observationModeOptions()
            : presetOptions.map((option) => ({ title: option, value: option })),
          current: typeof currentValue === "string" ? currentValue : undefined,
        })
      : await session.dialogs.prompt({
          title: "What should it be set to:",
          value: currentValue === undefined ? "" : String(currentValue),
        })
  if (rawValue === undefined) return

  try {
    const nextConfig = structuredClone(config)
    const nextValue = parseSharedConfigValue(currentValue, rawValue)
    setNestedValue(nextConfig, fieldPath, nextValue)
    const configPath = await writeSharedConfig(nextConfig)
    const importHint =
      fieldPath.endsWith("observationMode") && nextValue === "unified" ? unifiedImportFollowUp() : null
    await session.dialogs.alert({
      title: "Engram config updated",
      message: [`Saved settings to ${configPath}`, `Field: ${fieldPath}`, `Value: ${String(nextValue)}`, importHint]
        .filter((line): line is string => typeof line === "string")
        .join("\n"),
    })
  } catch (error) {
    await session.dialogs.alert({
      title: "Engram config update failed",
      message: error instanceof Error ? error.message : String(error),
    })
  }
}

export const runSetup = async (session: TuiSession) => {
  const mode = await session.dialogs.select<"cloud" | "local">({
    title: "Configure Engram",
    options: [
      { title: "Engram Cloud", value: "cloud", description: "Use the default Engram Cloud endpoint" },
      { title: "Self-hosted / local", value: "local", description: "Use a custom or localhost Engram base URL" },
    ],
  })
  if (!mode) return

  let baseUrl = DEFAULT_SETTINGS.baseUrl
  let apiKey: string | undefined
  if (mode === "local") {
    const entered = await session.dialogs.prompt({
      title: "Engram API base URL",
      placeholder: "http://127.0.0.1:8000",
      value: "http://127.0.0.1:8000",
    })
    if (entered === undefined) return
    baseUrl = entered.trim() || "http://127.0.0.1:8000"
    apiKey = await session.dialogs.prompt({
      title: "Optional Engram API key",
      placeholder: "Leave blank for local unauthenticated mode",
    })
    if (apiKey === undefined) return
  } else {
    apiKey = await session.dialogs.prompt({ title: "Engram API key", placeholder: "hch_..." })
    if (apiKey === undefined) return
    const validationError = validateCloudApiKey(apiKey)
    if (validationError) {
      await session.dialogs.alert({ title: "Engram setup incomplete", message: validationError })
      return
    }
  }

  const current = await readGlobalSettings()
  const sharedName = typeof current.peerName === "string" && current.peerName.trim() !== ""
  const enteredName = await session.dialogs.prompt({
    title: sharedName ? "Peer name (your other Engram tools use this name)" : "What should Engram call you?",
    placeholder: "Your Engram peer name",
    value: resolvePeerName(current.peerName),
  })
  if (enteredName === undefined) return
  const peerName = enteredName.trim() || resolvePeerName(current.peerName)
  const ids = resolveSessionPeerIds(peerName, current.hosts?.kilo?.aiPeer || DEFAULT_SETTINGS.aiPeer)
  if (ids.userPeerId === ids.agentPeerId) {
    await session.dialogs.alert({ title: "Engram setup incomplete", message: peerCollisionError(ids.userPeerId) })
    return
  }

  const workspace = await chooseWorkspace(session, current)
  if (workspace === undefined) return

  const configPath = await saveSettings({
    // A blank key keeps the saved one; writing "" would sign out every Engram tool that shares the file.
    apiKey: apiKey.trim() || undefined,
    baseUrl,
    peerName,
    hosts: { kilo: { workspace } },
  })
  await session.dialogs.alert({
    title: "Engram configured",
    message: [
      `Saved settings to ${configPath}`,
      `Base URL: ${baseUrl}`,
      `API key: ${apiKey.trim() ? "set" : current.apiKey?.trim() ? "unchanged" : mode === "local" ? "not required for localhost mode" : "not set"}`,
      `Peer name: ${peerName}`,
      `Workspace: ${workspace}`,
      "",
      "Every Engram tool on this machine reads the peer name from this file.",
    ].join("\n"),
  })
}

/** Workspaces that other Engram tools in the shared config already write to. */
export const otherToolWorkspaces = (raw: Record<string, unknown> | null) => {
  const hosts = raw && isRecord(raw.hosts) ? raw.hosts : {}
  const found = new Map<string, string>()
  for (const [tool, block] of Object.entries(hosts)) {
    if (tool === HOST_ID || !isRecord(block)) continue
    const workspace = typeof block.workspace === "string" ? block.workspace.trim() : ""
    if (workspace && !found.has(workspace)) found.set(workspace, tool)
  }
  return [...found].map(([workspace, tool]) => ({ workspace, tool }))
}

// Joining another tool's workspace only sets hosts.kilo.workspace; that tool's own settings stay as they are.
const chooseWorkspace = async (session: TuiSession, current: GlobalSettings) => {
  const currentWorkspace = current.hosts?.kilo?.workspace?.trim() || DEFAULT_SETTINGS.workspace
  const shared = otherToolWorkspaces(await readSharedConfig()).filter(({ workspace }) => workspace !== DEFAULT_SETTINGS.workspace)
  if (shared.length === 0) return currentWorkspace
  const options: DialogOption<string>[] = [
    { title: `Kilo's own (${DEFAULT_SETTINGS.workspace})`, value: DEFAULT_SETTINGS.workspace, description: "Kilo builds its own memory of you" },
    ...shared.map(({ workspace, tool }) => ({
      title: `Share with ${tool} (${workspace})`,
      value: workspace,
      description: `Kilo uses the memory ${tool} already has of you`,
    })),
  ]
  if (!options.some((option) => option.value === currentWorkspace)) {
    options.push({ title: `Keep ${currentWorkspace}`, value: currentWorkspace, description: "The workspace Kilo uses now" })
  }
  return session.dialogs.select<string>({
    title: "Which Engram workspace should Kilo use?",
    options,
    current: currentWorkspace,
  })
}

export const runImport = async (session: TuiSession) => {
  const settings = await readGlobalSettings()
  if (!isConfigured(settings)) {
    await session.dialogs.alert({
      title: "Engram import",
      message: "Run /engram:setup before importing local Kilo transcripts.",
    })
    return
  }

  const config = importConfigFromSettings(settings)
  let plan: Awaited<ReturnType<typeof planKiloImport>>
  try {
    plan = await planKiloImport({
      source: session.transcripts,
      workspaceId: config.workspaceId,
      sessionStrategy: config.sessionStrategy,
      userPeerId: config.userPeerId,
      agentPeerId: config.agentPeerId,
    })
  } catch (error) {
    await session.dialogs.alert({
      title: "Engram import",
      message: error instanceof Error ? error.message : String(error),
    })
    return
  }

  const preview = formatImportPreview(plan)
  if (plan.sessionCount === 0) {
    await session.dialogs.alert({ title: "Engram import", message: `${preview}\n\nNothing new to import.` })
    return
  }

  const choice = await session.dialogs.select<"preview" | "upload">({
    title: "Import local Kilo transcripts into Engram?",
    options: [
      { title: "Preview only", value: "preview", description: "Do not upload" },
      { title: "Upload now", value: "upload", description: "Sends conversation content to Engram" },
    ],
  })
  if (choice !== "upload") {
    if (choice === "preview") await session.dialogs.alert({ title: "Engram import preview", message: preview })
    return
  }

  try {
    const engram = createEngramClient({
      apiKey: config.apiKey,
      baseUrl: config.baseUrl,
      workspaceId: config.workspaceId,
    })
    const result = await executeKiloImport({
      source: session.transcripts,
      workspaceId: config.workspaceId,
      sessionStrategy: config.sessionStrategy,
      agentPeerId: config.agentPeerId,
      engram,
      userPeerId: config.userPeerId,
      agentObserveMe: config.agentObserveMe,
      observationMode: config.observationMode,
    })
    await session.dialogs.alert({
      title: "Engram import",
      message: [
        `Imported ${result.uploadedMessages} message(s) across ${result.uploadedSessions} session(s) into ${config.workspaceId}.`,
        result.errors.length > 0
          ? `${result.errors.length} session(s) failed.`
          : "Engram will reason over them; no restart needed.",
      ].join("\n"),
    })
  } catch (error) {
    await session.dialogs.alert({
      title: "Engram import failed",
      message: error instanceof Error ? error.message : String(error),
    })
  }
}

export const runRecall = async (session: TuiSession) => {
  const { kiloSessionId } = session.liveStatus(await readGlobalSettings())
  if (!kiloSessionId) {
    await session.dialogs.alert({
      title: "Engram recall",
      message: "Open a Kilo session to see the memory Engram added to it.",
    })
    return
  }
  const activity = await readActivity(resolveConfigPath(), kiloSessionId)
  await session.dialogs.view({ title: "Engram recall", body: recallMessage(activity) })
}

export const COMMANDS: readonly TuiCommandSpec[] = [
  {
    id: "engram.setup",
    title: "Engram Setup",
    description: "Configure Engram Cloud or local settings for Kilo",
    slash: "engram:setup",
    run: runSetup,
  },
  {
    id: "engram.status",
    title: "Engram Status",
    description: "Show Engram runtime health for the current Kilo session",
    slash: "engram:status",
    run: runStatus,
  },
  {
    id: "engram.recall",
    title: "Engram Recall",
    description: "Show the memory Engram added to this Kilo session",
    slash: "engram:recall",
    run: runRecall,
  },
  {
    id: "engram.settings",
    title: "Engram Settings",
    description: "Show effective Engram config values for Kilo",
    slash: "engram:settings",
    run: runSettings,
  },
  {
    id: "engram.config",
    title: "Engram Config",
    description: "Edit shared Engram config fields from ~/.engram/config.json",
    slash: "engram:config",
    run: runConfig,
  },
  {
    id: "engram.import",
    title: "Engram Import",
    description: "Preview or import local Kilo transcripts into Engram",
    slash: "engram:import",
    run: runImport,
  },
]

export const runGuarded = async (session: TuiSession, command: TuiCommandSpec) => {
  try {
    await command.run(session)
  } catch (error) {
    await session.dialogs.alert({
      title: command.title,
      message: error instanceof Error ? error.message : String(error),
    })
  }
}
