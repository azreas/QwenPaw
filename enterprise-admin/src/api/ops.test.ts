import { beforeEach, describe, expect, it, vi } from "vitest"
import { get, patch, post } from "./http"
import {
  getOpsOverview,
  getTenantOpsSummary,
  listTenantBadCases,
  listTenantBusinessTraces,
  markTenantBadCase,
  updateTenantBadCase,
} from "./ops"

vi.mock("./http", () => ({
  get: vi.fn(),
  patch: vi.fn(),
  post: vi.fn(),
}))

const trace = {
  id: "audit-1",
  tenant_id: "acme",
  agent_id: "wx_acme",
  session_id: "session-1",
  actor_id: "user-1",
  entrypoint: "webchat",
  ability_type: "skill",
  ability_name: "sales_report",
  duration_ms: 45,
  status: "failure",
  error_reason: "timeout",
  request_id: "req-1",
  trace_id: "trace-1",
  created_at: "2026-05-13T08:00:00+00:00",
}

describe("ops api", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("gets ops overview", async () => {
    vi.mocked(get).mockResolvedValue({
      total_tenants: 4,
      running_tenants: 3,
      unhealthy_tenants: 1,
      business_calls_24h: 20,
      failed_calls_24h: 2,
      failure_rate: 0.1,
      entrypoints: { webchat: 12 },
      top_failed_abilities: [],
    })

    const result = await getOpsOverview()

    expect(get).toHaveBeenCalledWith("/config/channels/wecom_tenant/ops/overview")
    expect(result.business_calls_24h).toBe(20)
  })

  it("gets tenant ops summary", async () => {
    vi.mocked(get).mockResolvedValue({
      tenant_id: "acme",
      agent_id: "wx_acme",
      health_status: "healthy",
      last_activity_at: "2026-05-13T08:10:00+00:00",
      business_calls_24h: 10,
      failed_calls_24h: 2,
      recent_failures: [trace],
    })

    const result = await getTenantOpsSummary("wx_acme")

    expect(get).toHaveBeenCalledWith(
      "/config/channels/wecom_tenant/tenants/wx_acme/ops/summary",
    )
    expect(result.health_status).toBe("healthy")
  })

  it("lists tenant business traces with query params", async () => {
    vi.mocked(get).mockResolvedValue({
      items: [trace],
      total: 1,
    })

    const result = await listTenantBusinessTraces("wx_acme", {
      ability_type: "skill",
      status: "failure",
      limit: 50,
    })

    expect(get).toHaveBeenCalledWith(
      "/config/channels/wecom_tenant/tenants/wx_acme/ops/traces",
      {
        params: {
          ability_type: "skill",
          status: "failure",
          limit: 50,
        },
      },
    )
    expect(result.items[0].ability_name).toBe("sales_report")
  })

  it("lists tenant bad cases", async () => {
    vi.mocked(get).mockResolvedValue({
      items: [
        {
          case_id: "case-audit-1",
          source_audit_id: "audit-1",
          source_request_id: "req-1",
          source_trace_id: "trace-1",
          category: "data_quality",
          status: "open",
          owner: "ops",
          note: "wrong answer",
          ability_type: "skill",
          ability_name: "sales_report",
          entrypoint: "webchat",
          created_at: "2026-05-13T08:00:00+00:00",
          updated_at: "2026-05-13T08:00:00+00:00",
        },
      ],
      total: 1,
    })

    const result = await listTenantBadCases("wx_acme")

    expect(get).toHaveBeenCalledWith(
      "/config/channels/wecom_tenant/tenants/wx_acme/bad-cases",
    )
    expect(result.items[0].case_id).toBe("case-audit-1")
  })

  it("marks tenant bad case", async () => {
    vi.mocked(post).mockResolvedValue({
      case_id: "case-audit-1",
      source_audit_id: "audit-1",
      source_request_id: "req-1",
      source_trace_id: "trace-1",
      category: "platform_runtime",
      status: "open",
      owner: "ops",
      note: "timeout",
      ability_type: "mcp",
      ability_name: "erp",
      entrypoint: "webchat",
      created_at: "2026-05-13T08:00:00+00:00",
      updated_at: "2026-05-13T08:00:00+00:00",
    })

    await markTenantBadCase("wx_acme", {
      source_audit_id: "audit-1",
      source_request_id: "req-1",
      source_trace_id: "trace-1",
      category: "platform_runtime",
      owner: "ops",
      note: "timeout",
    })

    expect(post).toHaveBeenCalledWith(
      "/config/channels/wecom_tenant/tenants/wx_acme/bad-cases",
      {
        source_audit_id: "audit-1",
        source_request_id: "req-1",
        source_trace_id: "trace-1",
        category: "platform_runtime",
        owner: "ops",
        note: "timeout",
      },
    )
  })

  it("updates tenant bad case with encoded case id", async () => {
    vi.mocked(patch).mockResolvedValue({
      case_id: "case-audit 1",
      status: "triaged",
      category: "permission_config",
      owner: "ops",
      note: "assigned",
    })

    await updateTenantBadCase("wx_acme", "case-audit 1", {
      status: "triaged",
      owner: "ops",
    })

    expect(patch).toHaveBeenCalledWith(
      "/config/channels/wecom_tenant/tenants/wx_acme/bad-cases/case-audit%201",
      {
        status: "triaged",
        owner: "ops",
      },
    )
  })
})
