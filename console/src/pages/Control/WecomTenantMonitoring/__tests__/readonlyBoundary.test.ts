import assert from "node:assert/strict";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, it } from "node:test";

const monitoringDir = join(
  process.cwd(),
  "src/pages/Control/WecomTenantMonitoring",
);
const forbidden = [
  "startWecomTenant",
  "stopWecomTenant",
  "restartWecomTenant",
  "reloadWecomTenant",
  "deleteWecomTenant",
  "batchStartWecomTenants",
  "batchStopWecomTenants",
  "batchRestartWecomTenants",
  "updateWecomTenant",
  "createWecomTenant",
];

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? walk(path) : [path];
  });
}

describe("WecomTenantMonitoring readonly boundary", () => {
  it("does not call tenant write APIs from monitoring pages", () => {
    const source = walk(monitoringDir)
      .filter((path) => /\.(ts|tsx)$/.test(path))
      .filter((path) => !path.includes("__tests__"))
      .map((path) => readFileSync(path, "utf8"))
      .join("\n");

    for (const apiName of forbidden) {
      assert.equal(
        source.includes(apiName),
        false,
        `${apiName} must stay in tenant management pages`,
      );
    }
  });
});
