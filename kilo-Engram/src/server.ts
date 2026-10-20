import { createEngramRuntimePlugin } from "./index.js"
import { PACKAGE_ID } from "./engram-client.js"

export const server = createEngramRuntimePlugin({
  configPath: process.env.KILO_ENGRAM_CONFIG_PATH,
})

// Kilo requires an exported id when the plugin loads from a file path; it matches the npm name.
const plugin = {
  id: PACKAGE_ID,
  server,
}

export default plugin
