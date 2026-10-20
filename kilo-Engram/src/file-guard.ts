import path from "node:path"
import { activityDir } from "./activity.js"
import { isRecord, userHomeDir } from "./core.js"

export const ENGRAM_FILES_BLOCKED =
  "Engram blocked this tool call because it touches Engram's config, which holds the user's API key. Call engram_status to see Engram's settings, or engram_setup to set Engram up."

// `.engram` as a whole path segment in any case, since macOS and Windows file names ignore case.
const ENGRAM_DIR = /(^|[^\w.-])\.engram(?![\w-])/i
// Kilo's read, write, edit, glob, grep and bash tools name files in these arguments.
const PATH_ARGS = ["filePath", "path", "pattern", "workdir"]
const PATCH_FILE = /^\*\*\* (?:Add File|Update File|Delete File|Move to): (.+)$/gm

const spellings = (file: string) => {
  const home = userHomeDir()
  if (!file.startsWith(`${home}${path.sep}`)) return [file]
  const rest = file.slice(home.length)
  return [file, `~${rest}`, `$HOME${rest}`, `\${HOME}${rest}`]
}

const within = (file: string, dir: string) => file === dir || file.startsWith(`${dir}${path.sep}`)

/** Whether a tool call names `~/.engram`, the config file in use, or the activity folder. Commands are matched as text, so this stops a model that means well, not one that hides the path. */
export const touchesEngramFiles = (args: unknown, configPath: string, directory: string) => {
  if (!isRecord(args)) return false
  const resolvedPaths = [configPath, activityDir(configPath)].map((file) => path.resolve(file))
  const protectedPaths = resolvedPaths.map((file) => file.toLowerCase())
  const names = resolvedPaths.flatMap(spellings).map((name) => name.toLowerCase())
  const mentions = (text: string) => ENGRAM_DIR.test(text) || names.some((name) => text.toLowerCase().includes(name))
  const workdir = typeof args.workdir === "string" ? path.resolve(directory, args.workdir) : directory
  const paths = PATH_ARGS.map((key) => args[key]).filter((value): value is string => typeof value === "string")
  if (typeof args.patchText === "string") paths.push(...[...args.patchText.matchAll(PATCH_FILE)].map((match) => match[1].trim()))
  if (typeof args.command === "string" && mentions(args.command)) return true
  return paths.some((value) => {
    const resolved = path.resolve(workdir, value).toLowerCase()
    return mentions(value) || protectedPaths.some((file) => within(resolved, file))
  })
}
