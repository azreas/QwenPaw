import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { summarizeReadiness } from "../runtimeTypes.ts";

describe("runtime api helpers", () => {
  it("summarizes degraded readiness as serviceable", () => {
    const summary = summarizeReadiness({
      ready: true,
      status: "degraded",
      components: [
        { name: "storage", status: "ok" },
        { name: "redis", status: "degraded" },
      ],
    });

    assert.equal(summary.status, "degraded");
    assert.equal(summary.ready, true);
    assert.equal(summary.failedComponents.length, 0);
  });

  it("lists down components as failed", () => {
    const summary = summarizeReadiness({
      ready: false,
      status: "down",
      components: [
        { name: "storage", status: "down" },
        { name: "audit", status: "ok" },
      ],
    });

    assert.deepEqual(summary.failedComponents, ["storage"]);
  });
});
