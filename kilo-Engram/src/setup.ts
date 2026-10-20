import path from "node:path"
import { userHomeDir } from "./core.js"
import { createEngramClient } from "./engram-client.js"

/** Kilo's global config directory: `$XDG_CONFIG_HOME/kilo`, else `~/.config/kilo`, on every platform. */
export const kiloConfigDir = () =>
  path.join(process.env.XDG_CONFIG_HOME?.trim() || path.join(userHomeDir(), ".config"), "kilo")

/** Throws when Engram rejects the key. Gets or creates the workspace Kilo will write to. */
export const checkEngramConnection = async (input: { apiKey: string; baseUrl: string; workspace: string }) => {
  await createEngramClient({ apiKey: input.apiKey, baseUrl: input.baseUrl, workspaceId: input.workspace }).getMetadata()
}
