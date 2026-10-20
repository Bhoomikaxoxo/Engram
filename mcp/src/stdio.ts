import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import * as Sentry from "@sentry/bun";
import { engramClients, parseEnvConfig, sentryOptions } from "./config.js";
import { createServer } from "./server.js";

declare const process: {
  env: Record<string, string | undefined>;
  exit(code?: number): never;
};

Sentry.init(sentryOptions({ SENTRY_DSN: process.env.SENTRY_DSN }));

try {
  const config = parseEnvConfig({
    ENGRAM_API_KEY: process.env.ENGRAM_API_KEY,
    ENGRAM_API_URL: process.env.ENGRAM_API_URL,
    ENGRAM_WORKSPACE_ID: process.env.ENGRAM_WORKSPACE_ID,
    ENGRAM_TIMEOUT_MS: process.env.ENGRAM_TIMEOUT_MS,
  });
  // No HTTP caller on stdio, so only X-Engram-Host is sent.
  const server = createServer({ config, ...engramClients(config) });
  await server.connect(new StdioServerTransport());
} catch (e) {
  const message = e instanceof Error ? e.message : String(e);
  console.error(message);
  process.exit(1);
}
