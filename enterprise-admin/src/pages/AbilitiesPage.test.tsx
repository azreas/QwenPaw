import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import AbilitiesPage from "./AbilitiesPage"
import {
  createTenantMcpClient,
  deleteTenantMcpClient,
  deleteTenantSkill,
  installTenantSkill,
  listTenantMcpClients,
  listTenantSkills,
  listTenantTools,
  testTenantMcpClient,
  toggleTenantMcpClient,
  toggleTenantSkill,
  toggleTenantTool,
  updateTenantToolAsyncExecution,
} from "@/api/abilities"
import { listWecomTenants } from "@/api/tenants"

vi.mock("@/api/tenants", () => ({
  listWecomTenants: vi.fn(),
}))

vi.mock("@/api/abilities", () => ({
  createTenantMcpClient: vi.fn(),
  deleteTenantMcpClient: vi.fn(),
  deleteTenantSkill: vi.fn(),
  installTenantSkill: vi.fn(),
  listTenantSkills: vi.fn(),
  listTenantTools: vi.fn(),
  toggleTenantSkill: vi.fn(),
  listTenantMcpClients: vi.fn(),
  toggleTenantMcpClient: vi.fn(),
  testTenantMcpClient: vi.fn(),
  toggleTenantTool: vi.fn(),
  updateTenantToolAsyncExecution: vi.fn(),
}))

const tenant = {
  tenant_id: "acme",
  agent_id: "wx_acme",
  workspace_dir: "D:/tenants/wx_acme",
  exists: true,
  initialized: true,
  running: true,
  updated_at: "2026-05-13T08:00:00+00:00",
  chat_count: 3,
  job_count: 1,
  source: "workspace",
}

const initialSkill = {
  name: "sales_report",
  description: "sales",
  source: "workspace",
  enabled: false,
  installed: true,
  installable: true,
  channels: ["wecom"],
  tags: ["finance"],
  requirements: [],
  updated_at: null,
  last_call_at: null,
  last_call_status: "failure",
  last_error_reason: "timeout",
  last_duration_ms: 1200,
}

const enabledSkill = {
  ...initialSkill,
  enabled: true,
  last_call_status: "success",
  last_error_reason: null,
  last_duration_ms: 300,
}

const initialMcp = {
  client_key: "crm",
  name: "CRM",
  description: "crm client",
  enabled: true,
  transport: "streamable-http",
  url: "https://example.test/mcp",
  command: "",
  args: [],
  cwd: "",
  headers: {},
  env: {},
  last_call_at: null,
  last_call_status: "success",
  last_error_reason: null,
  last_duration_ms: 200,
  last_test_at: null,
  last_test_status: "timeout",
  last_test_detail: "timeout",
}

const disabledMcp = {
  ...initialMcp,
  enabled: false,
  last_test_status: "ok",
  last_test_detail: "ok",
}

const initialTool = {
  name: "read_file",
  description: "读取文件",
  enabled: true,
  async_execution: false,
  icon: "",
}

const asyncTool = {
  ...initialTool,
  async_execution: true,
}

describe("AbilitiesPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(listWecomTenants).mockResolvedValue({ tenants: [tenant] })
    vi.mocked(listTenantSkills).mockResolvedValue([initialSkill])
    vi.mocked(listTenantMcpClients).mockResolvedValue([initialMcp])
    vi.mocked(listTenantTools).mockResolvedValue([initialTool])
    vi.mocked(installTenantSkill).mockResolvedValue({ success: true, name: "sales_report" })
    vi.mocked(deleteTenantSkill).mockResolvedValue({ success: true, name: "sales_report" })
    vi.mocked(toggleTenantTool).mockResolvedValue(asyncTool)
    vi.mocked(updateTenantToolAsyncExecution).mockResolvedValue(asyncTool)
    vi.mocked(createTenantMcpClient).mockResolvedValue(initialMcp)
    vi.mocked(deleteTenantMcpClient).mockResolvedValue({ message: "deleted" })
  })

  it("renders skills and mcp tabs", async () => {
    render(<AbilitiesPage />)

    expect(await screen.findByText("业务能力")).toBeInTheDocument()
    expect(await screen.findByText("sales_report")).toBeInTheDocument()
    expect(screen.getByText("finance")).toBeInTheDocument()
    expect(screen.getByText("Skills 总数")).toBeInTheDocument()

    await userEvent.click(screen.getByRole("tab", { name: "MCP" }))
    expect(await screen.findByText("crm")).toBeInTheDocument()
    expect(screen.getByText("CRM")).toBeInTheDocument()
  })

  it("toggles skill and reloads list", async () => {
    vi.mocked(listTenantSkills)
      .mockResolvedValueOnce([initialSkill])
      .mockResolvedValueOnce([enabledSkill])

    render(<AbilitiesPage />)

    await userEvent.click(
      await screen.findByRole("button", { name: "启用 sales_report" }),
    )

    await waitFor(() => {
      expect(toggleTenantSkill).toHaveBeenCalledWith("wx_acme", "sales_report")
    })
    expect(listTenantSkills).toHaveBeenCalledTimes(2)
    expect(listTenantMcpClients).toHaveBeenCalledTimes(2)
    expect(listTenantTools).toHaveBeenCalledTimes(2)
  })

  it("installs and deletes skills", async () => {
    vi.mocked(listTenantSkills)
      .mockResolvedValueOnce([{ ...initialSkill, installed: false, installable: true }])
      .mockResolvedValueOnce([enabledSkill])
      .mockResolvedValueOnce([enabledSkill])

    render(<AbilitiesPage />)

    await userEvent.click(
      await screen.findByRole("button", { name: "安装 sales_report" }),
    )

    await waitFor(() => {
      expect(installTenantSkill).toHaveBeenCalledWith("wx_acme", {
        skill_id: "sales_report",
        overwrite: false,
      })
    })

    await userEvent.click(
      await screen.findByRole("button", { name: "删除 sales_report" }),
    )

    await waitFor(() => {
      expect(deleteTenantSkill).toHaveBeenCalledWith("wx_acme", "sales_report")
    })
  })

  it("tests mcp client and reloads list", async () => {
    vi.mocked(listTenantMcpClients)
      .mockResolvedValueOnce([initialMcp])
      .mockResolvedValueOnce([disabledMcp])

    render(<AbilitiesPage />)

    await userEvent.click(screen.getByRole("tab", { name: "MCP" }))
    await userEvent.click(
      await screen.findByRole("button", { name: "测试 crm" }),
    )

    await waitFor(() => {
      expect(testTenantMcpClient).toHaveBeenCalledWith("wx_acme", "crm")
    })
    expect(listTenantSkills).toHaveBeenCalledTimes(2)
    expect(listTenantMcpClients).toHaveBeenCalledTimes(2)
    expect(listTenantTools).toHaveBeenCalledTimes(2)
  })

  it("toggles mcp client and reloads list", async () => {
    vi.mocked(listTenantMcpClients)
      .mockResolvedValueOnce([initialMcp])
      .mockResolvedValueOnce([disabledMcp])

    render(<AbilitiesPage />)

    await userEvent.click(screen.getByRole("tab", { name: "MCP" }))
    await userEvent.click(
      await screen.findByRole("button", { name: "停用 crm" }),
    )

    await waitFor(() => {
      expect(toggleTenantMcpClient).toHaveBeenCalledWith("wx_acme", "crm")
    })
    expect(listTenantSkills).toHaveBeenCalledTimes(2)
    expect(listTenantMcpClients).toHaveBeenCalledTimes(2)
    expect(listTenantTools).toHaveBeenCalledTimes(2)
  })

  it("creates and deletes mcp client", async () => {
    render(<AbilitiesPage />)

    await userEvent.click(screen.getByRole("tab", { name: "MCP" }))
    await userEvent.click(await screen.findByRole("button", { name: "新建 MCP" }))
    await userEvent.type(screen.getByLabelText("Client Key"), "erp")
    await userEvent.type(screen.getByLabelText("名称"), "ERP MCP")
    await userEvent.type(screen.getByLabelText("命令"), "uvx")
    await userEvent.click(screen.getByRole("button", { name: /OK|确.*定/ }))

    await waitFor(() => {
      expect(createTenantMcpClient).toHaveBeenCalledWith("wx_acme", {
        client_key: "erp",
        client: {
          name: "ERP MCP",
          command: "uvx",
          url: undefined,
        },
      })
    })

    await userEvent.click(
      await screen.findByRole("button", { name: "删除 MCP crm" }),
    )

    await waitFor(() => {
      expect(deleteTenantMcpClient).toHaveBeenCalledWith("wx_acme", "crm")
    })
  })

  it("shows empty tenants without calling ability apis", async () => {
    vi.mocked(listWecomTenants).mockResolvedValue({ tenants: [] })

    render(<AbilitiesPage />)

    expect(await screen.findByText("暂无租户")).toBeInTheDocument()
    expect(listTenantSkills).not.toHaveBeenCalled()
    expect(listTenantMcpClients).not.toHaveBeenCalled()
    expect(listTenantTools).not.toHaveBeenCalled()
  })

  it("does not show internal page completeness details", async () => {
    render(<AbilitiesPage />)

    expect(await screen.findByRole("heading", { name: "业务能力" })).toBeInTheDocument()
    expect(screen.queryByText("页面完整性")).not.toBeInTheDocument()
    expect(screen.queryByText("Console 退出关系")).not.toBeInTheDocument()
  })

  it("shows staged catalog and real tools tab", async () => {
    render(<AbilitiesPage />)

    const catalogTab = await screen.findByRole("tab", { name: "能力目录" })
    const toolsTab = screen.getByRole("tab", { name: "Tools" })

    expect(catalogTab).toBeInTheDocument()
    expect(toolsTab).toBeInTheDocument()

    await userEvent.click(catalogTab)
    expect(
      await screen.findByText(/全局能力目录、版本、依赖校验和安全扫描/),
    ).toBeInTheDocument()

    await userEvent.click(toolsTab)
    expect(await screen.findByText("read_file")).toBeInTheDocument()

    await userEvent.click(
      await screen.findByRole("button", { name: "停用 Tool read_file" }),
    )
    await waitFor(() => {
      expect(toggleTenantTool).toHaveBeenCalledWith("wx_acme", "read_file")
    })

    await userEvent.click(screen.getByRole("button", { name: "切换异步 read_file" }))
    await waitFor(() => {
      expect(updateTenantToolAsyncExecution).toHaveBeenCalledWith(
        "wx_acme",
        "read_file",
        { async_execution: true },
      )
    })
  })
})
