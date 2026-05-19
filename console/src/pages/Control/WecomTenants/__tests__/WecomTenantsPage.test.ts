import assert from "node:assert/strict";
import { describe, it } from "node:test";
import type { WecomTenantSummary } from "../../../../api/types";
import {
  getRequestedAgentId,
  resolveSelectedTenant,
  shouldShowMissingRequestedTenant,
  shouldShowMobileDetail,
} from "../pageModel.ts";

function tenant(agentId: string): WecomTenantSummary {
  return {
    tenant_id: agentId.replace("wx_", ""),
    agent_id: agentId,
    workspace_dir: `D:/tenants/${agentId}`,
    exists: true,
    initialized: true,
    running: false,
    chat_count: 0,
    job_count: 0,
    source: "workspace",
  };
}

describe("WecomTenantsPage", () => {
  it("selects the requested tenant when it exists", () => {
    const tenants = [tenant("wx_1"), tenant("wx_2")];
    assert.equal(resolveSelectedTenant(tenants, "wx_2")?.agent_id, "wx_2");
  });

  it("falls back to the first tenant when the selected id disappears", () => {
    const tenants = [tenant("wx_1"), tenant("wx_2")];
    assert.equal(resolveSelectedTenant(tenants, "wx_missing")?.agent_id, "wx_1");
  });

  it("shows mobile detail only after an explicit mobile selection", () => {
    assert.equal(shouldShowMobileDetail("wx_1", false), false);
    assert.equal(shouldShowMobileDetail("wx_1", true), true);
    assert.equal(shouldShowMobileDetail(null, true), false);
  });

  it("returns null when tenant list is empty", () => {
    assert.equal(resolveSelectedTenant([], "wx_1"), null);
  });

  it("returns null when selectedAgentId is null and list is empty", () => {
    assert.equal(resolveSelectedTenant([], null), null);
  });

  it("falls back to first tenant when selectedAgentId is null", () => {
    const tenants = [tenant("wx_1"), tenant("wx_2")];
    assert.equal(resolveSelectedTenant(tenants, null)?.agent_id, "wx_1");
  });

  it("reads requested agent id from query string", () => {
    assert.equal(getRequestedAgentId("?agentId=wx_alpha"), "wx_alpha");
    assert.equal(getRequestedAgentId("?foo=bar"), null);
  });

  it("detects missing requested tenant without falling back silently", () => {
    const tenants = [tenant("wx_alpha")];
    assert.equal(shouldShowMissingRequestedTenant(tenants, "wx_missing"), true);
    assert.equal(shouldShowMissingRequestedTenant(tenants, "wx_alpha"), false);
  });
});
