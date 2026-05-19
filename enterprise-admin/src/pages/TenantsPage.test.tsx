import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import TenantsPage from "./TenantsPage"
import {
  createWecomTenant,
  listWecomTenants,
  startWecomTenant,
} from "@/api/tenants"
import {
  listTenantMcpClients,
  listTenantSkills,
  listTenantTools,
} from "@/api/abilities"
import { getTenantLlmRouting, getTenantModel } from "@/api/models"
import { diagnoseTenantEntryConfig } from "@/api/entryConfig"
import {
  getTenantSecuritySettings,
  getTenantSystemPrompts,
  listTenantTemplates,
  putTenantSecuritySettings,
  putTenantSystemPrompts,
} from "@/api/agentConfig"
import {
  getTenantHealth,
  listTenantCronJobs,
  listTenantMemoryFiles,
  listTenantWorkspaceFiles,
  pauseTenantCronJob,
} from "@/api/tenantRuntime"

vi.mock("@/api/tenants", () => ({
  createWecomTenant: vi.fn(),
  listWecomTenants: vi.fn(),
  restartWecomTenant: vi.fn(),
  startWecomTenant: vi.fn(),
  stopWecomTenant: vi.fn(),
}))

vi.mock("@/api/tenantRuntime", () => ({
  getTenantHealth: vi.fn(),
  listTenantCronJobs: vi.fn(),
  listTenantMemoryFiles: vi.fn(),
  listTenantWorkspaceFiles: vi.fn(),
  pauseTenantCronJob: vi.fn(),
  resumeTenantCronJob: vi.fn(),
  runTenantCronJob: vi.fn(),
}))

vi.mock("@/api/abilities", () => ({
  listTenantMcpClients: vi.fn(),
  listTenantSkills: vi.fn(),
  listTenantTools: vi.fn(),
}))

vi.mock("@/api/models", () => ({
  getTenantLlmRouting: vi.fn(),
  getTenantModel: vi.fn(),
}))

vi.mock("@/api/entryConfig", () => ({
  diagnoseTenantEntryConfig: vi.fn(),
}))

vi.mock("@/api/agentConfig", () => ({
  getTenantSecuritySettings: vi.fn(),
  getTenantSystemPrompts: vi.fn(),
  listTenantTemplates: vi.fn(),
  putTenantSecuritySettings: vi.fn(),
  putTenantSystemPrompts: vi.fn(),
}))

const tenant = {
  tenant_id: "acme",
  agent_id: "wx_acme",
  workspace_dir: "D:/tenants/wx_acme",
  exists: true,
  initialized: true,
  running: false,
  updated_at: "2026-05-13T08:00:00+00:00",
  chat_count: 4,
  job_count: 2,
  source: "workspace",
}

describe("TenantsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(listWecomTenants).mockResolvedValue({ tenants: [tenant] })
    vi.mocked(getTenantHealth).mockResolvedValue({
      agent_id: "wx_acme",
      status: "healthy",
      checks: {
        workspace_exists: true,
        agent_json_valid: true,
      },
    })
    vi.mocked(listTenantWorkspaceFiles).mockResolvedValue({
      files: [{ filename: "AGENTS.md", size: 128 }],
    })
    vi.mocked(listTenantMemoryFiles).mockResolvedValue({
      files: [{ filename: "profile.json", size: 64 }],
    })
    vi.mocked(listTenantCronJobs).mockResolvedValue([
      {
        id: "job-1",
        name: "每日摘要",
        enabled: true,
        task_type: "text",
      },
    ])
    vi.mocked(listTenantSkills).mockResolvedValue([
      {
        name: "sales_report",
        description: "sales",
        source: "workspace",
        enabled: true,
        installed: true,
        installable: false,
        channels: [],
        tags: [],
        requirements: [],
      },
    ])
    vi.mocked(listTenantTools).mockResolvedValue([
      { name: "read_file", enabled: true, description: "读取文件", async_execution: false, icon: "" },
    ])
    vi.mocked(listTenantMcpClients).mockResolvedValue([
      {
        client_key: "crm",
        name: "CRM",
        description: "crm",
        enabled: true,
        transport: "streamable-http",
        url: "https://example.test/mcp",
        command: "",
        args: [],
        cwd: "",
        headers: {},
        env: {},
      },
    ])
    vi.mocked(getTenantModel).mockResolvedValue({
      provider_id: "dashscope",
      model: "qwen-max",
    })
    vi.mocked(getTenantLlmRouting).mockResolvedValue({
      enabled: true,
      mode: "cloud_first",
      local: { provider_id: "ollama", model: "qwen2.5" },
      cloud: { provider_id: "dashscope", model: "qwen-max" },
    })
    vi.mocked(diagnoseTenantEntryConfig).mockResolvedValue({
      agent_id: "wx_acme",
      status: "ok",
      checks: {
        workspace_exists: true,
        wecom_bot_id_configured: true,
      },
      messages: [],
    })
    vi.mocked(listTenantTemplates).mockResolvedValue({
      templates: [
        {
          template_id: "default",
          display_name: "默认成员模板",
          default_model: "qwen-max",
          default_prompt_files: ["AGENTS.md"],
          default_skills: ["sales_report"],
          default_tools: ["read_file"],
          default_task_templates: [],
        },
      ],
    })
    vi.mocked(getTenantSystemPrompts).mockResolvedValue({
      files: ["AGENTS.md", "SOUL.md"],
    })
    vi.mocked(getTenantSecuritySettings).mockResolvedValue({
      approval_level: "AUTO",
      tool_guard_rules: [],
    })
    vi.mocked(putTenantSystemPrompts).mockResolvedValue({
      files: ["AGENTS.md", "SOUL.md", "PROFILE.md"],
    })
    vi.mocked(putTenantSecuritySettings).mockResolvedValue({
      approval_level: "SMART",
      tool_guard_rules: [],
    })
    vi.mocked(pauseTenantCronJob).mockResolvedValue({ paused: true })
  })

  it("renders tenant list and stats", async () => {
    render(<TenantsPage />)

    expect(await screen.findByText("租户总数")).toBeInTheDocument()
    expect(screen.getByText("wx_acme")).toBeInTheDocument()
    // "已初始化" 同时出现在统计卡片标题和表格状态 Tag，用 getAllBy 验证至少存在
    expect(screen.getAllByText("已初始化").length).toBeGreaterThan(0)
  })

  it("creates tenant and reloads list", async () => {
    vi.mocked(createWecomTenant).mockResolvedValue({
      ...tenant,
      tenant_id: "beta",
      agent_id: "wx_beta",
    })

    render(<TenantsPage />)
    await userEvent.click(await screen.findByRole("button", { name: /新建租户/ }))
    await userEvent.type(screen.getByLabelText("租户 ID"), "beta")
    // Ant Design Modal 的确认按钮渲染为 "确 认"（含空格），使用正则匹配
    await userEvent.click(screen.getByRole("button", { name: /确.*认/ }))

    await waitFor(() => {
      expect(createWecomTenant).toHaveBeenCalledWith({
        tenant_id: "beta",
        start: false,
      })
    })
    expect(listWecomTenants).toHaveBeenCalledTimes(2)
  })

  it("starts selected tenant", async () => {
    vi.mocked(startWecomTenant).mockResolvedValue({ ...tenant, running: true })

    render(<TenantsPage />)
    await userEvent.click(await screen.findByRole("button", { name: "启动" }))

    await waitFor(() => {
      expect(startWecomTenant).toHaveBeenCalledWith("wx_acme")
    })
  })

  it("does not show internal page completeness details", async () => {
    render(<TenantsPage />)

    expect(await screen.findByRole("heading", { name: "租户管理" })).toBeInTheDocument()
    expect(screen.queryByText("页面完整性")).not.toBeInTheDocument()
    expect(screen.queryByText("Console 退出关系")).not.toBeInTheDocument()
  })

  it("shows staged tenant entry configuration and diagnostics in detail drawer", async () => {
    render(<TenantsPage />)

    await userEvent.click(await screen.findByRole("button", { name: "详情" }))

    expect(await screen.findByText("基础信息")).toBeInTheDocument()
    expect(screen.getByText("入口配置")).toBeInTheDocument()
    expect(screen.getByText("运行资源")).toBeInTheDocument()
    expect(screen.getByText("诊断与审计")).toBeInTheDocument()

    await userEvent.click(screen.getByRole("tab", { name: "入口配置" }))
    expect(
      screen.getByText(/企微回调、可信 IP、Bot 参数和 WebChat 会话设置/),
    ).toBeInTheDocument()
  })

  it("loads tenant runtime resources and runs cron action in detail drawer", async () => {
    render(<TenantsPage />)

    await userEvent.click(await screen.findByRole("button", { name: "详情" }))
    await userEvent.click(screen.getByRole("tab", { name: "运行资源" }))

    expect(await screen.findByText("健康检查")).toBeInTheDocument()
    expect(screen.getByText("Workspace 文件")).toBeInTheDocument()
    expect(screen.getByText("AGENTS.md")).toBeInTheDocument()
    expect(screen.getByText("profile.json")).toBeInTheDocument()
    expect(screen.getByText("入口诊断")).toBeInTheDocument()
    expect(screen.getByText("模型路由")).toBeInTheDocument()
    expect(screen.getByText("dashscope / qwen-max")).toBeInTheDocument()
    expect(screen.getByText("Skills / MCP / Tools")).toBeInTheDocument()
    expect(screen.getByText("Skill: sales_report")).toBeInTheDocument()
    expect(screen.getByText("MCP: CRM")).toBeInTheDocument()
    expect(screen.getByText("Tool: read_file")).toBeInTheDocument()
    expect(screen.getByText("导入导出与模板")).toBeInTheDocument()
    expect(screen.getByText("每日摘要")).toBeInTheDocument()

    await userEvent.click(screen.getByRole("button", { name: "暂停" }))

    await waitFor(() => {
      expect(pauseTenantCronJob).toHaveBeenCalledWith("wx_acme", "job-1")
    })
    expect(getTenantHealth).toHaveBeenCalledWith("wx_acme")
    expect(listTenantCronJobs).toHaveBeenCalledWith("wx_acme")
    expect(listTenantSkills).toHaveBeenCalledWith("wx_acme")
    expect(listTenantMcpClients).toHaveBeenCalledWith("wx_acme")
    expect(getTenantLlmRouting).toHaveBeenCalledWith("wx_acme")
    expect(diagnoseTenantEntryConfig).toHaveBeenCalledWith("wx_acme")
  })

  it("shows platform templates and saves tenant-local agent config", async () => {
    render(<TenantsPage />)

    await userEvent.click(await screen.findByRole("button", { name: "详情" }))
    await userEvent.click(screen.getByRole("tab", { name: "Agent 配置" }))

    expect(await screen.findByText("平台模板")).toBeInTheDocument()
    expect(screen.getByText("默认成员模板")).toBeInTheDocument()
    expect(screen.getByText(/模板应用阶段化开放/)).toBeInTheDocument()
    expect(screen.getByText("Agent Prompt 文件")).toBeInTheDocument()
    expect(screen.getByText("Agent 安全等级")).toBeInTheDocument()

    await userEvent.click(screen.getByRole("combobox", { name: "Agent 安全等级" }))
    await userEvent.click(
      await screen.findByText("SMART", {
        selector: ".ant-select-item-option-content",
      }),
    )

    await waitFor(() => {
      expect(putTenantSecuritySettings).toHaveBeenCalledWith("wx_acme", {
        approval_level: "SMART",
        tool_guard_rules: [],
      })
      expect(listTenantTemplates).toHaveBeenCalled()
      expect(getTenantSystemPrompts).toHaveBeenCalledWith("wx_acme")
    })
  })
})
