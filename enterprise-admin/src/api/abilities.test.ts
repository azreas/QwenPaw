import { beforeEach, describe, expect, it, vi } from "vitest"
import { del, get, patch, post, put } from "./http"
import {
  createTenantMcpClient,
  deleteTenantMcpClient,
  deleteTenantSkill,
  installTenantSkill,
  listTenantTools,
  listTenantMcpClients,
  listTenantSkills,
  testTenantMcpClient,
  toggleTenantMcpClient,
  toggleTenantSkill,
  toggleTenantTool,
  updateTenantMcpClient,
  updateTenantToolAsyncExecution,
} from "./abilities"

vi.mock("./http", () => ({
  del: vi.fn(),
  get: vi.fn(),
  patch: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
}))

describe("abilities api", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("列出租户 skills", async () => {
    vi.mocked(get).mockResolvedValue([
      {
        name: "sales_report",
        description: "销售报表",
        source: "workspace",
        enabled: true,
        installed: true,
        installable: false,
        channels: ["wecom_tenant"],
        tags: ["sales"],
        requirements: [],
      },
    ])

    const result = await listTenantSkills("wx_demo")

    expect(get).toHaveBeenCalledWith(
      "/config/channels/wecom_tenant/tenants/wx_demo/skills",
    )
    expect(result[0].name).toBe("sales_report")
  })

  it("切换 skill 时对 agentId 和 skillId 做 URL 编码", async () => {
    vi.mocked(patch).mockResolvedValue({
      skill_id: "skill/a b",
      enabled: false,
      message: "ok",
    })

    await toggleTenantSkill("wx team/a", "skill/a b")

    expect(patch).toHaveBeenCalledWith(
      "/config/channels/wecom_tenant/tenants/wx%20team%2Fa/skills/skill%2Fa%20b/toggle",
    )
  })

  it("安装和删除 skill 时调用租户级接口", async () => {
    vi.mocked(post).mockResolvedValue({ success: true, name: "demo" })
    vi.mocked(del).mockResolvedValue({ success: true, name: "demo" })

    await installTenantSkill("wx_demo", { skill_id: "demo", overwrite: true })
    await deleteTenantSkill("wx_demo", "demo/a b")

    expect(post).toHaveBeenCalledWith(
      "/config/channels/wecom_tenant/tenants/wx_demo/skills/install",
      { skill_id: "demo", overwrite: true },
    )
    expect(del).toHaveBeenCalledWith(
      "/config/channels/wecom_tenant/tenants/wx_demo/skills/demo%2Fa%20b",
    )
  })

  it("管理 Tools 时调用租户级接口", async () => {
    vi.mocked(get).mockResolvedValue([])
    vi.mocked(patch).mockResolvedValue({
      name: "read_file",
      enabled: true,
      description: "",
      async_execution: false,
      icon: "",
    })

    await listTenantTools("wx_demo")
    await toggleTenantTool("wx_demo", "read/file")
    await updateTenantToolAsyncExecution("wx_demo", "read/file", {
      async_execution: true,
    })

    expect(get).toHaveBeenCalledWith(
      "/config/channels/wecom_tenant/tenants/wx_demo/tools",
    )
    expect(patch).toHaveBeenNthCalledWith(
      1,
      "/config/channels/wecom_tenant/tenants/wx_demo/tools/read%2Ffile/toggle",
    )
    expect(patch).toHaveBeenNthCalledWith(
      2,
      "/config/channels/wecom_tenant/tenants/wx_demo/tools/read%2Ffile/async-execution",
      { async_execution: true },
    )
  })

  it("列出租户 MCP clients", async () => {
    vi.mocked(get).mockResolvedValue([
      {
        client_key: "erp",
        name: "ERP",
        description: "ERP MCP",
        enabled: true,
        transport: "streamable_http",
        url: "https://mcp.example.com",
        command: "",
        args: [],
        cwd: "",
        headers: {},
        env: {},
      },
    ])

    const result = await listTenantMcpClients("wx_demo")

    expect(get).toHaveBeenCalledWith(
      "/config/channels/wecom_tenant/tenants/wx_demo/mcp",
    )
    expect(result[0].client_key).toBe("erp")
  })

  it("切换和测试 MCP client 时对 key 做 URL 编码", async () => {
    vi.mocked(patch).mockResolvedValue({
      client_key: "erp/main server",
      name: "ERP",
      description: "ERP MCP",
      enabled: false,
      transport: "streamable_http",
      url: "https://mcp.example.com",
      command: "",
      args: [],
      cwd: "",
      headers: {},
      env: {},
    })
    vi.mocked(post).mockResolvedValue({
      status: "ok",
      message: "connected",
      latency_ms: 88,
    })

    await toggleTenantMcpClient("wx_demo", "erp/main server")
    await testTenantMcpClient("wx_demo", "erp/main server")

    expect(patch).toHaveBeenCalledWith(
      "/config/channels/wecom_tenant/tenants/wx_demo/mcp/erp%2Fmain%20server/toggle",
    )
    expect(post).toHaveBeenCalledWith(
      "/config/channels/wecom_tenant/tenants/wx_demo/mcp/erp%2Fmain%20server/test",
    )
  })

  it("创建、更新、删除 MCP client 时调用租户级接口", async () => {
    vi.mocked(post).mockResolvedValue({ client_key: "local" })
    vi.mocked(put).mockResolvedValue({ client_key: "local" })
    vi.mocked(del).mockResolvedValue({ message: "deleted" })

    await createTenantMcpClient("wx_demo", {
      client_key: "local",
      client: { name: "Local", command: "uvx" },
    })
    await updateTenantMcpClient("wx_demo", "local/key", {
      name: "Local",
      command: "uvx",
    })
    await deleteTenantMcpClient("wx_demo", "local/key")

    expect(post).toHaveBeenCalledWith(
      "/config/channels/wecom_tenant/tenants/wx_demo/mcp",
      { client_key: "local", client: { name: "Local", command: "uvx" } },
    )
    expect(put).toHaveBeenCalledWith(
      "/config/channels/wecom_tenant/tenants/wx_demo/mcp/local%2Fkey",
      { name: "Local", command: "uvx" },
    )
    expect(del).toHaveBeenCalledWith(
      "/config/channels/wecom_tenant/tenants/wx_demo/mcp/local%2Fkey",
    )
  })
})
