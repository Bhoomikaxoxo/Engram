import { expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import * as sdk from "@engram-ai/sdk";
import installed from "@engram-ai/sdk/package.json";

// wrangler bundles whatever is in node_modules without a typecheck, so a
// checkout whose install predates a lockfile bump ships tools that call SDK
// methods the bundle lacks. A Worker built against SDK 2.2.0 failed
// workspace_chat ("client.chat is not a function"), the scope tools and
// get_conclusions, and silently dropped scope/sessions recall bounds.
test("installed @engram-ai/sdk matches the lockfile", () => {
  const lock = readFileSync(new URL("../bun.lock", import.meta.url), "utf8");
  const pinned = lock.match(/"@engram-ai\/sdk": \["@engram-ai\/sdk@([^"]+)"/)?.[1];
  expect(pinned).toBeDefined();
  expect(installed.version).toBe(pinned!);
});

// The option-level gaps (scope / sessions on chat and get_representation)
// are only visible on the wire; scope-read-options.test.ts and
// chat-evidence.test.ts assert those.
test("installed @engram-ai/sdk has the surface the tools call", () => {
  expect(typeof sdk.Engram.prototype.chat).toBe("function"); // workspace_chat
  expect(typeof sdk.Engram.prototype.scopes).toBe("function"); // list_scopes
  expect(typeof sdk.Scope).toBe("function"); // get_scope_status, get_scope_sessions, …

  const engram = new sdk.Engram({
    apiKey: "test-key",
    baseURL: "https://engram.test",
    workspaceId: "test-workspace",
  });
  expect(typeof engram.conclusions?.getMany).toBe("function"); // get_conclusions
  expect(typeof engram.conclusions?.list).toBe("function"); // get_derived_conclusions
});
