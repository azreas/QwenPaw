import assert from "node:assert/strict";
import { describe, it } from "node:test";
import type { AgentSummary } from "../../../../api/types/agents.ts";
import type { TokenUsageSummary } from "../../../../api/types/tokenUsage.ts";
import type {
  WecomTenantHealthResponse,
  WecomTenantSummary,
} from "../../../../api/types/wecomTenant.ts";
import {
  buildAttentionItems,
  buildStatsParams,
  buildTenantRows,
  buildTokenDateRows,
  buildTokenModelRows,
  computeKpis,
  filterRows,
} from "../model.ts";
import type { TenantRow } from "../model.ts";

// ---- helpers ----

function tenant(
  agentId: string,
  overrides: Partial<WecomTenantSummary> = {},
): WecomTenantSummary {
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
    ...overrides,
  };
}

function agent(id: string, overrides: Partial<AgentSummary> = {}): AgentSummary {
  return {
    id,
    name: `Agent ${id}`,
    description: "",
    workspace_dir: `D:/tenants/${id}`,
    enabled: true,
    ...overrides,
  };
}

function health(
  agentId: string,
  status: WecomTenantHealthResponse["status"],
): WecomTenantHealthResponse {
  return { agent_id: agentId, status, checks: {} };
}

function tokenSummary(
  prompt: number,
  completion: number,
  calls: number,
): TokenUsageSummary {
  return {
    total_prompt_tokens: prompt,
    total_completion_tokens: completion,
    total_calls: calls,
    by_model: {},
    by_date: {},
  };
}

// ---- tests ----

describe("buildTenantRows", () => {
  it("merges tenant, health, agent, and token data", () => {
    const tenants = [tenant("wx_1", { running: true, chat_count: 5 })];
    const healthMap = { wx_1: health("wx_1", "healthy") };
    const agents = [agent("wx_1", { name: "My Agent" })];
    const tokenMap = { wx_1: tokenSummary(100, 200, 10) };

    const rows = buildTenantRows(tenants, healthMap, agents, tokenMap);
    assert.equal(rows.length, 1);
    assert.equal(rows[0].agentName, "My Agent");
    assert.equal(rows[0].running, true);
    assert.equal(rows[0].health, "healthy");
    assert.equal(rows[0].tokens, 300);
    assert.equal(rows[0].calls, 10);
    assert.equal(rows[0].chatCount, 5);
  });

  it("uses agentId as fallback name when agent is missing", () => {
    const tenants = [tenant("wx_unknown")];
    const rows = buildTenantRows(tenants, {}, [], {});
    assert.equal(rows[0].agentName, "wx_unknown");
    assert.equal(rows[0].health, null);
    assert.equal(rows[0].tokens, 0);
  });
});

describe("computeKpis", () => {
  it("counts running, stopped, and unhealthy correctly", () => {
    const rows: TenantRow[] = [
      { key: "1", tenantId: "t1", agentId: "a1", agentName: "A1", running: true, health: "healthy", model: null, workspaceDir: "", exists: true, initialized: true, updatedAt: null, chatCount: 2, jobCount: 0, tokens: 100, calls: 5 },
      { key: "2", tenantId: "t2", agentId: "a2", agentName: "A2", running: false, health: "unhealthy", model: null, workspaceDir: "", exists: true, initialized: true, updatedAt: null, chatCount: 0, jobCount: 0, tokens: 0, calls: 0 },
      { key: "3", tenantId: "t3", agentId: "a3", agentName: "A3", running: true, health: "degraded", model: null, workspaceDir: "", exists: true, initialized: true, updatedAt: null, chatCount: 1, jobCount: 0, tokens: 50, calls: 2 },
    ];
    const agents = [agent("a1"), agent("a2", { enabled: false }), agent("a3")];

    const kpis = computeKpis(rows, agents);
    assert.equal(kpis.totalTenants, 3);
    assert.equal(kpis.runningTenants, 2);
    assert.equal(kpis.stoppedTenants, 1);
    assert.equal(kpis.unhealthyTenants, 1);
    assert.equal(kpis.enabledAgents, 2);
    assert.equal(kpis.totalTokens, 150);
    assert.equal(kpis.totalCalls, 7);
    assert.equal(kpis.totalChats, 3);
  });

  it("handles empty rows", () => {
    const kpis = computeKpis([], []);
    assert.equal(kpis.totalTenants, 0);
    assert.equal(kpis.totalTokens, 0);
  });
});

describe("filterRows", () => {
  const rows: TenantRow[] = [
    { key: "1", tenantId: "t1", agentId: "wx_alpha", agentName: "Alpha Bot", running: true, health: "healthy", model: null, workspaceDir: "", exists: true, initialized: true, updatedAt: null, chatCount: 0, jobCount: 0, tokens: 0, calls: 0 },
    { key: "2", tenantId: "t2", agentId: "wx_beta", agentName: "Beta Bot", running: false, health: "unhealthy", model: null, workspaceDir: "", exists: true, initialized: true, updatedAt: null, chatCount: 0, jobCount: 0, tokens: 0, calls: 0 },
    { key: "3", tenantId: "t3", agentId: "wx_gamma", agentName: "Gamma Bot", running: true, health: "degraded", model: null, workspaceDir: "", exists: true, initialized: true, updatedAt: null, chatCount: 0, jobCount: 0, tokens: 0, calls: 0 },
  ];

  it("filters by running status", () => {
    assert.equal(filterRows(rows, { status: "running" }).length, 2);
    assert.equal(filterRows(rows, { status: "stopped" }).length, 1);
    assert.equal(filterRows(rows, { status: "all" }).length, 3);
  });

  it("filters by health status", () => {
    assert.equal(filterRows(rows, { health: "unhealthy" }).length, 1);
    assert.equal(filterRows(rows, { health: "healthy" }).length, 1);
  });

  it("filters by search (matches agentId, tenantId, agentName)", () => {
    assert.equal(filterRows(rows, { search: "alpha" }).length, 1);
    assert.equal(filterRows(rows, { search: "t2" }).length, 1);
    assert.equal(filterRows(rows, { search: "Gamma" }).length, 1);
    assert.equal(filterRows(rows, { search: "nonexistent" }).length, 0);
  });

  it("combines multiple filters", () => {
    assert.equal(
      filterRows(rows, { status: "running", health: "degraded" }).length,
      1,
    );
  });
});

describe("buildTokenModelRows", () => {
  it("extracts model rows from by_model", () => {
    const summary: TokenUsageSummary = {
      total_prompt_tokens: 0,
      total_completion_tokens: 0,
      total_calls: 0,
      by_model: {
        "gpt-4": { provider_id: "openai", model: "gpt-4", prompt_tokens: 100, completion_tokens: 200, call_count: 5 },
      },
      by_date: {},
    };
    const rows = buildTokenModelRows(summary);
    assert.equal(rows.length, 1);
    assert.equal(rows[0].model, "gpt-4");
    assert.equal(rows[0].promptTokens, 100);
  });

  it("returns empty for null summary", () => {
    assert.deepEqual(buildTokenModelRows(null), []);
  });
});

describe("buildTokenDateRows", () => {
  it("sorts by date ascending", () => {
    const summary: TokenUsageSummary = {
      total_prompt_tokens: 0,
      total_completion_tokens: 0,
      total_calls: 0,
      by_model: {},
      by_date: {
        "2026-04-10": { prompt_tokens: 10, completion_tokens: 20, call_count: 1 },
        "2026-04-08": { prompt_tokens: 5, completion_tokens: 15, call_count: 2 },
      },
    };
    const rows = buildTokenDateRows(summary);
    assert.equal(rows.length, 2);
    assert.equal(rows[0].date, "2026-04-08");
    assert.equal(rows[1].date, "2026-04-10");
  });
});

describe("buildAttentionItems", () => {
  it("flags unhealthy tenants as error", () => {
    const rows: TenantRow[] = [
      { key: "1", tenantId: "t1", agentId: "a1", agentName: "A1", running: true, health: "unhealthy", model: null, workspaceDir: "", exists: true, initialized: true, updatedAt: null, chatCount: 0, jobCount: 0, tokens: 0, calls: 0 },
    ];
    const items = buildAttentionItems(rows, [agent("a1")]);
    assert.equal(items.length, 1);
    assert.equal(items[0].severity, "error");
    assert.equal(items[0].reason, "unhealthy");
  });

  it("flags missing workspace as warning", () => {
    const rows: TenantRow[] = [
      { key: "1", tenantId: "t1", agentId: "a1", agentName: "A1", running: true, health: "healthy", model: null, workspaceDir: "", exists: false, initialized: false, updatedAt: null, chatCount: 0, jobCount: 0, tokens: 0, calls: 0 },
    ];
    const items = buildAttentionItems(rows, [agent("a1")]);
    assert.ok(items.some((i) => i.reason === "workspaceMissing"));
  });

  it("flags missing agent as warning", () => {
    const rows: TenantRow[] = [
      { key: "1", tenantId: "t1", agentId: "a1", agentName: "A1", running: true, health: "healthy", model: null, workspaceDir: "", exists: true, initialized: true, updatedAt: null, chatCount: 0, jobCount: 0, tokens: 0, calls: 0 },
    ];
    // no agents passed
    const items = buildAttentionItems(rows, []);
    assert.ok(items.some((i) => i.reason === "agentMissing"));
  });

  it("flags disabled agent as info", () => {
    const rows: TenantRow[] = [
      { key: "1", tenantId: "t1", agentId: "a1", agentName: "A1", running: true, health: "healthy", model: null, workspaceDir: "", exists: true, initialized: true, updatedAt: null, chatCount: 0, jobCount: 0, tokens: 0, calls: 0 },
    ];
    const items = buildAttentionItems(rows, [agent("a1", { enabled: false })]);
    assert.ok(items.some((i) => i.reason === "agentDisabled" && i.severity === "info"));
  });

  it("returns empty for healthy, enabled tenants", () => {
    const rows: TenantRow[] = [
      { key: "1", tenantId: "t1", agentId: "a1", agentName: "A1", running: true, health: "healthy", model: null, workspaceDir: "", exists: true, initialized: true, updatedAt: null, chatCount: 0, jobCount: 0, tokens: 0, calls: 0 },
    ];
    const items = buildAttentionItems(rows, [agent("a1")]);
    assert.equal(items.length, 0);
  });
});

describe("buildStatsParams", () => {
  it("returns undefined when no range", () => {
    assert.equal(buildStatsParams(undefined), undefined);
  });

  it("maps date range to start_date / end_date", () => {
    const params = buildStatsParams(["2026-04-01", "2026-04-30"]);
    assert.deepEqual(params, { start_date: "2026-04-01", end_date: "2026-04-30" });
  });
});
