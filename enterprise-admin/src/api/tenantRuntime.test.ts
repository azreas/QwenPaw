import { beforeEach, describe, expect, it, vi } from "vitest"
import { get, post } from "./http"
import {
  getTenantHealth,
  listTenantCronJobs,
  listTenantMemoryFiles,
  listTenantWorkspaceFiles,
  pauseTenantCronJob,
  resumeTenantCronJob,
  runTenantCronJob,
} from "./tenantRuntime"

vi.mock("./http", () => ({
  get: vi.fn(),
  post: vi.fn(),
}))

describe("tenantRuntime api", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("loads tenant runtime resources with encoded agent id", async () => {
    vi.mocked(get).mockResolvedValue({ files: [] })

    await getTenantHealth("wx demo/a")
    await listTenantWorkspaceFiles("wx demo/a")
    await listTenantMemoryFiles("wx demo/a")
    await listTenantCronJobs("wx demo/a")

    expect(get).toHaveBeenNthCalledWith(
      1,
      "/config/channels/wecom_tenant/tenants/wx%20demo%2Fa/health",
    )
    expect(get).toHaveBeenNthCalledWith(
      2,
      "/config/channels/wecom_tenant/tenants/wx%20demo%2Fa/files",
    )
    expect(get).toHaveBeenNthCalledWith(
      3,
      "/config/channels/wecom_tenant/tenants/wx%20demo%2Fa/memory",
    )
    expect(get).toHaveBeenNthCalledWith(
      4,
      "/config/channels/wecom_tenant/tenants/wx%20demo%2Fa/cron",
    )
  })

  it("runs cron actions with encoded job id", async () => {
    vi.mocked(post).mockResolvedValue({})

    await pauseTenantCronJob("wx_demo", "job/a b")
    await resumeTenantCronJob("wx_demo", "job/a b")
    await runTenantCronJob("wx_demo", "job/a b")

    expect(post).toHaveBeenNthCalledWith(
      1,
      "/config/channels/wecom_tenant/tenants/wx_demo/cron/job%2Fa%20b/pause",
    )
    expect(post).toHaveBeenNthCalledWith(
      2,
      "/config/channels/wecom_tenant/tenants/wx_demo/cron/job%2Fa%20b/resume",
    )
    expect(post).toHaveBeenNthCalledWith(
      3,
      "/config/channels/wecom_tenant/tenants/wx_demo/cron/job%2Fa%20b/run",
    )
  })
})
