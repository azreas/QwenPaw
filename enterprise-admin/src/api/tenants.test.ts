import { beforeEach, describe, expect, it, vi } from "vitest"
import { get, post } from "./http"
import {
  createWecomTenant,
  listWecomTenants,
  restartWecomTenant,
  startWecomTenant,
  stopWecomTenant,
} from "./tenants"

vi.mock("./http", () => ({
  get: vi.fn(),
  post: vi.fn(),
}))

const tenant = {
  tenant_id: "acme",
  agent_id: "wx_acme",
  workspace_dir: "D:/data/tenants/wx_acme",
  exists: true,
  initialized: true,
  running: false,
  updated_at: "2026-05-13T08:00:00+00:00",
  chat_count: 2,
  job_count: 1,
  source: "workspace",
}

describe("tenants api", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("列出企微租户", async () => {
    vi.mocked(get).mockResolvedValue({ tenants: [tenant] })

    const result = await listWecomTenants()

    expect(get).toHaveBeenCalledWith("/config/channels/wecom_tenant/tenants")
    expect(result.tenants[0].agent_id).toBe("wx_acme")
  })

  it("创建租户（可选启动标志）", async () => {
    vi.mocked(post).mockResolvedValue({ ...tenant, running: true })

    const result = await createWecomTenant({ tenant_id: "acme", start: true })

    expect(post).toHaveBeenCalledWith("/config/channels/wecom_tenant/tenants", {
      tenant_id: "acme",
      start: true,
    })
    expect(result.running).toBe(true)
  })

  it("按 agent_id 启动、停止、重启租户", async () => {
    vi.mocked(post).mockResolvedValue(tenant)

    await startWecomTenant("wx_acme")
    await stopWecomTenant("wx_acme")
    await restartWecomTenant("wx_acme")

    expect(post).toHaveBeenNthCalledWith(
      1,
      "/config/channels/wecom_tenant/tenants/wx_acme/start",
    )
    expect(post).toHaveBeenNthCalledWith(
      2,
      "/config/channels/wecom_tenant/tenants/wx_acme/stop",
    )
    expect(post).toHaveBeenNthCalledWith(
      3,
      "/config/channels/wecom_tenant/tenants/wx_acme/restart",
    )
  })
})
