import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { resolveStaticSelectedKey } from "../navigationModel.ts";

describe("navigationModel", () => {
  it("selects tenant monitoring for monitoring overview", () => {
    assert.equal(
      resolveStaticSelectedKey("/wecom-tenants/monitoring"),
      "wecom-tenant-monitoring",
    );
  });

  it("selects tenant monitoring for monitoring drilldown", () => {
    assert.equal(
      resolveStaticSelectedKey("/wecom-tenants/monitoring/wx_alpha"),
      "wecom-tenant-monitoring",
    );
  });

  it("selects tenant management for management page", () => {
    assert.equal(
      resolveStaticSelectedKey("/wecom-tenants"),
      "wecom-tenant-management",
    );
  });

  it("selects platform overview for platform entry", () => {
    assert.equal(resolveStaticSelectedKey("/platform"), "platform");
  });

  it("selects platform policies for policy editor", () => {
    assert.equal(
      resolveStaticSelectedKey("/platform/policies"),
      "platform-policies",
    );
  });

  it("keeps regular routes unchanged", () => {
    assert.equal(resolveStaticSelectedKey("/token-usage"), "token-usage");
    assert.equal(resolveStaticSelectedKey("/agents"), "agents");
  });
});
