import { beforeEach, describe, expect, it, vi } from "vitest"
import {
  getDiagnosticsOverview,
  getTenantDiagnosticsSnapshot,
} from "./diagnostics"
import { diagnoseTenantEntryConfig } from "./entryConfig"
import { getEnterpriseReadiness, getReady } from "./runtime"
import { getTenantHealth } from "./tenantRuntime"

vi.mock("./runtime", () => ({
  getEnterpriseReadiness: vi.fn(),
  getReady: vi.fn(),
}))

vi.mock("./tenantRuntime", () => ({
  getTenantHealth: vi.fn(),
}))

vi.mock("./entryConfig", () => ({
  diagnoseTenantEntryConfig: vi.fn(),
}))

describe("diagnostics api", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(getReady).mockResolvedValue({ ready: true })
    vi.mocked(getEnterpriseReadiness).mockResolvedValue({ status: "ready" })
    vi.mocked(getTenantHealth).mockResolvedValue({
      agent_id: "wx_acme",
      status: "healthy",
      checks: {},
    })
    vi.mocked(diagnoseTenantEntryConfig).mockResolvedValue({
      agent_id: "wx_acme",
      status: "ok",
      checks: {},
      messages: [],
    })
  })

  it("loads platform diagnostics overview", async () => {
    const result = await getDiagnosticsOverview()

    expect(result.ready.ready).toBe(true)
    expect(result.enterprise.status).toBe("ready")
    expect(getReady).toHaveBeenCalled()
    expect(getEnterpriseReadiness).toHaveBeenCalled()
  })

  it("loads tenant diagnostics snapshot", async () => {
    await getTenantDiagnosticsSnapshot("wx_acme")

    expect(getTenantHealth).toHaveBeenCalledWith("wx_acme")
    expect(diagnoseTenantEntryConfig).toHaveBeenCalledWith("wx_acme")
  })
})
