import { render, screen, waitFor } from "@testing-library/react"
import { describe, it, expect, vi, beforeEach } from "vitest"

// Mock the auth module
vi.mock("@/api/auth", () => ({
  getAuthStatus: vi.fn().mockResolvedValue({
    authenticated: true,
    username: "admin",
    role: "platform_admin",
  }),
  login: vi.fn(),
  logout: vi.fn(),
}))

vi.mock("@/api/runtime", () => ({
  getVersion: vi.fn().mockResolvedValue({ version: "1.0.0" }),
  getReady: vi.fn().mockResolvedValue({
    ready: false,
    components: [
      {
        name: "storage",
        status: "ok",
        details: { backend: "sqlite" },
      },
      {
        name: "audit",
        status: "degraded",
        message: "not configured",
      },
      {
        name: "runtime_extensions",
        status: "down",
        message: "extension probe failed",
        details: { gateway: "unreachable" },
      },
    ],
  }),
  getEnterpriseReadiness: vi.fn().mockResolvedValue({
    enabled: true,
    features: {
      authz: true,
      audit: true,
      quota: true,
      observability: true,
      policy: true,
      security: true,
      reliability: true,
      compliance: true,
    },
    storageBackend: "sqlite",
    status: "ready" as const,
  }),
}))

vi.mock("@/api/tenants", () => ({
  listWecomTenants: vi.fn().mockResolvedValue({
    tenants: [
      {
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
      },
    ],
  }),
}))

vi.mock("@/api/models", () => ({
  getTenantLlmRouting: vi.fn().mockResolvedValue({
    enabled: true,
    mode: "cloud_first",
    local: { provider_id: "ollama", model: "qwen2.5" },
    cloud: { provider_id: "dashscope", model: "qwen-max" },
  }),
  getTenantModel: vi.fn().mockResolvedValue({
    provider_id: "dashscope",
    model: "qwen-max",
  }),
  putTenantLlmRouting: vi.fn(),
  putTenantModel: vi.fn(),
}))

vi.mock("@/api/entryConfig", () => ({
  diagnoseTenantEntryConfig: vi.fn().mockResolvedValue({
    agent_id: "wx_acme",
    status: "ok",
    checks: { workspace_exists: true },
    messages: [],
  }),
  getTenantEntryConfig: vi.fn().mockResolvedValue({
    wecom: {
      enabled: true,
      bot_id: "bot-old",
      secret_set: true,
      media_dir: null,
      welcome_text: "hello",
      share_session_in_group: true,
      max_reconnect_attempts: -1,
      streaming_enabled: false,
      require_mention: false,
      dm_policy: "open",
      group_policy: "open",
      allow_from: ["corp-a"],
      deny_message: "",
    },
    webchat: {
      enabled: true,
      media_dir: "media",
      user_data_dir: "users",
      require_mention: false,
      dm_policy: "allowlist",
      group_policy: "open",
      allow_from: ["u1"],
      deny_message: "blocked",
    },
  }),
  putTenantEntryConfig: vi.fn(),
}))

vi.mock("@/api/evaluation", () => ({
  convertBadCasesToEval: vi.fn(),
  createTenantEvalDataset: vi.fn(),
  createTenantEvalExecution: vi.fn(),
  getSampleEvalDataset: vi.fn(),
  getTenantAccuracyReport: vi.fn(),
  listTenantEvalDatasets: vi.fn().mockResolvedValue({
    items: [
      {
        id: "dataset-1",
        tenant_id: "acme",
        name: "一期验收集",
        description: "覆盖核心指标和权限边界",
        created_at: "2026-05-13T08:00:00+00:00",
        updated_at: "2026-05-13T08:00:00+00:00",
        items: [],
      },
    ],
    total: 1,
  }),
  listTenantEvalExecutions: vi.fn().mockResolvedValue({
    items: [],
    total: 0,
  }),
}))

vi.mock("@/api/quota", () => ({
  getQuotaConfigSummary: vi.fn().mockResolvedValue({
    enabled: true,
    redis_url_set: true,
    default_limits: [
      {
        dimension: "http.request",
        window: "minute",
        max_value: 300,
        resource: "*",
      },
    ],
  }),
  getTokenUsageDetails: vi.fn().mockResolvedValue([
    {
      date: "2026-05-16",
      provider_id: "dashscope",
      model: "qwen-max",
      agent_id: "wx_acme",
      prompt_tokens: 100,
      completion_tokens: 50,
      call_count: 2,
    },
  ]),
  getTokenUsageSummary: vi.fn().mockResolvedValue({
    total_prompt_tokens: 100,
    total_completion_tokens: 50,
    total_calls: 2,
    by_date: {
      "2026-05-16": {
        prompt_tokens: 100,
        completion_tokens: 50,
        call_count: 2,
      },
    },
  }),
  listQuotaAuditEvents: vi.fn().mockResolvedValue({
    events: [],
    count: 0,
  }),
}))

vi.mock("@/api/security", () => ({
  listPermissionDenials: vi.fn().mockResolvedValue({
    events: [],
    count: 0,
  }),
  listTenantPolicies: vi.fn().mockResolvedValue({
    policies: [
      {
        policy_id: "default",
        display_name: "默认成员策略",
        allow_model_switch: true,
        allowed_models: [],
        allow_skill_create: true,
        allow_skill_upload_zip: true,
        allow_skill_hub_import: true,
        allow_tools: true,
        allowed_tools: [],
        allow_mcp: true,
        allowed_mcp_transports: ["sse", "http"],
        allow_tasks: true,
        max_cron_jobs: 20,
        min_cron_interval_minutes: 5,
        allow_task_run_now: true,
        allow_task_tools: true,
        task_timeout_seconds: 120,
        file_upload_limit_mb: 100,
        token_quota_monthly: null,
        advanced_config_enabled: false,
      },
    ],
  }),
  putTenantPolicy: vi.fn(),
}))

vi.mock("@/api/backups", () => ({
  getBackupDetail: vi.fn(),
  getBackupProductionPolicy: vi.fn().mockResolvedValue({
    schedule: "0 3 * * *",
    retention_days: 90,
    remote_store: "filesystem",
    integrity: "sha256",
  }),
  listBackups: vi.fn().mockResolvedValue([]),
  runBackupRestoreDrill: vi.fn(),
}))

vi.mock("@/api/diagnostics", () => ({
  getDiagnosticsOverview: vi.fn().mockResolvedValue({
    ready: {
      ready: false,
      components: [
        {
          name: "audit",
          status: "degraded",
          message: "repository unavailable",
        },
      ],
    },
    enterprise: {
      status: "degraded",
      checks: [
        {
          name: "authz",
          status: "pass",
          required: true,
          message: "ok",
        },
      ],
    },
  }),
  getTenantDiagnosticsSnapshot: vi.fn().mockResolvedValue({
    health: {
      agent_id: "wx_acme",
      status: "healthy",
      checks: { workspace_exists: true },
    },
    entry: {
      agent_id: "wx_acme",
      status: "ok",
      checks: { wecom_bot_id_configured: true },
      messages: [],
    },
  }),
}))

vi.mock("@/api/ops", () => ({
  getOpsOverview: vi.fn().mockResolvedValue({
    total_tenants: 1,
    running_tenants: 1,
    unhealthy_tenants: 0,
    business_calls_24h: 12,
    failed_calls_24h: 2,
    failure_rate: 0.167,
    entrypoints: {
      webchat: 10,
      wecom_bot: 2,
    },
    top_failed_abilities: [],
  }),
  listTenantBadCases: vi.fn().mockResolvedValue({
    items: [],
    total: 0,
  }),
}))

vi.mock("@/api/policies", () => ({
  listPolicies: vi.fn().mockResolvedValue({
    policies: [
      {
        policy_id: "default",
        display_name: "默认成员策略",
        allow_model_switch: true,
        allowed_models: [],
        allow_skill_create: true,
        allow_skill_upload_zip: true,
        allow_skill_hub_import: true,
        allow_tools: true,
        allowed_tools: [],
        allow_mcp: true,
        allowed_mcp_transports: ["sse", "http"],
        allow_tasks: true,
        max_cron_jobs: 20,
        min_cron_interval_minutes: 5,
        allow_task_run_now: true,
        allow_task_tools: true,
        task_timeout_seconds: 120,
        file_upload_limit_mb: 100,
        token_quota_monthly: null,
        advanced_config_enabled: false,
      },
    ],
  }),
  listTemplates: vi.fn().mockResolvedValue({
    templates: [
      {
        template_id: "default",
        display_name: "默认成员模板",
        default_model: null,
        default_prompt_files: [],
        default_skills: [],
        default_tools: [],
        default_task_templates: [],
      },
    ],
  }),
  listPlatformTenants: vi.fn().mockResolvedValue({
    tenants: [],
  }),
  savePolicy: vi.fn(),
  saveTemplate: vi.fn(),
  deletePolicy: vi.fn(),
  deleteTemplate: vi.fn(),
}))

vi.mock("@/api/metrics", () => ({
  getRawMetrics: vi.fn().mockResolvedValue(`http_requests_total{method="GET",route="/api/version"} 3
runtime_active 1
`),
  parsePrometheusMetrics: vi.fn().mockReturnValue({
    raw: `http_requests_total{method="GET",route="/api/version"} 3
runtime_active 1
`,
    metrics: [
      {
        name: "http_requests_total",
        type: "untyped",
        help: "",
        sampleCount: 1,
        latestValue: 3,
      },
      {
        name: "runtime_active",
        type: "untyped",
        help: "",
        sampleCount: 1,
        latestValue: 1,
      },
    ],
    samples: [
      {
        name: "http_requests_total",
        labels: { method: "GET", route: "/api/version" },
        value: 3,
        raw: `http_requests_total{method="GET",route="/api/version"} 3`,
      },
      {
        name: "runtime_active",
        labels: {},
        value: 1,
        raw: "runtime_active 1",
      },
    ],
    metricCount: 2,
    sampleCount: 2,
    seriesCount: 2,
    typeCount: 2,
    unavailable: false,
  }),
}))

vi.mock("@/api/settings", () => ({
  exportComplianceAudit: vi.fn(),
  getPlatformSettingsSummary: vi.fn().mockResolvedValue({
    frontend: {
      mode: "enterprise",
      console_enabled: false,
      root_entry: "enterprise-admin",
      console_access: "disabled",
    },
    storage: {
      backend: "sqlite",
      database_url_configured: true,
      database_url_redacted: true,
    },
    audit: {
      storage_available: true,
      backend: "sqlite",
    },
    compliance: {
      export_available: true,
      formats: ["json", "csv"],
      reason: "",
    },
    controlled_switches: [],
  }),
}))

async function importApp(pathname = "/enterprise-admin/dashboard") {
  vi.resetModules()
  window.history.pushState({}, "", pathname)
  return import("./App")
}

describe("App", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders without crashing", async () => {
    const { default: App } = await importApp()

    render(<App />)
    // 验证应用能够正常渲染（至少没有崩溃）
    await waitFor(() => {
      expect(document.body).toBeInTheDocument()
    })
  }, 20000)

  it("renders readiness components with failure reasons", async () => {
    const { default: App } = await importApp()

    render(<App />)

    expect(await screen.findByText("审计")).toBeInTheDocument()
    expect(screen.queryByText("页面完整性")).not.toBeInTheDocument()
    expect(screen.queryByText("Console 退出关系")).not.toBeInTheDocument()
    expect(screen.getByText("运行时扩展")).toBeInTheDocument()
    expect(screen.getByText("not configured")).toBeInTheDocument()
    expect(
      screen.getByText("extension probe failed；gateway: unreachable"),
    ).toBeInTheDocument()
    expect(screen.getByText("24h 调用")).toBeInTheDocument()
    expect(screen.getByText("失败调用")).toBeInTheDocument()
  }, 20000)

  it("renders evaluation route without crashing", async () => {
    const { default: App } = await importApp("/enterprise-admin/evaluation")

    render(<App />)

    expect(
      await screen.findByRole("heading", { name: "验收测评" }),
    ).toBeInTheDocument()
  }, 20000)

  it("renders model governance route with tenant routing controls", async () => {
    const { default: App } = await importApp("/enterprise-admin/models")

    render(<App />)

    expect(
      await screen.findByRole("heading", { name: "模型治理" }),
    ).toBeInTheDocument()
    expect(screen.getByText("租户模型授权与模型路由")).toBeInTheDocument()
    expect(screen.getByText("平台模型库存阶段化开放")).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByLabelText("Model")).toHaveValue("qwen-max")
    })
  }, 20000)

  it("renders entry config route with tenant-local controls", async () => {
    const { default: App } = await importApp("/enterprise-admin/entry-config")

    render(<App />)

    expect(
      await screen.findByRole("heading", { name: "入口配置" }),
    ).toBeInTheDocument()
    expect(screen.getByText("企微 Bot 与 WebChat 租户入口治理")).toBeInTheDocument()
    expect(
      screen.getByText("WebChat 平台级登录参数仍由环境变量管理"),
    ).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByLabelText("WeCom Bot ID")).toHaveValue("bot-old")
    })
  }, 20000)

  it("renders policies route with native page instead of staged placeholder", async () => {
    const { default: App } = await importApp("/enterprise-admin/policies")

    render(<App />)

    expect(
      await screen.findByRole("heading", { name: "策略配置" }),
    ).toBeInTheDocument()
    expect(
      screen.getByText("平台策略、租户模板与影响范围"),
    ).toBeInTheDocument()
    expect(screen.getByText("策略变更为平台级配置")).toBeInTheDocument()
    expect(
      screen.queryByText("Phase 3/4 阶段化开放"),
    ).not.toBeInTheDocument()
    expect(screen.queryByText("Console 退出关系")).not.toBeInTheDocument()
    expect(
      screen.queryByText(/返回 Console|使用 Console|Console 兜底/),
    ).not.toBeInTheDocument()
  }, 20000)

  it("renders diagnostics route without Console fallback", async () => {
    const { default: App } = await importApp("/enterprise-admin/diagnostics")

    render(<App />)

    expect(
      await screen.findByRole("heading", { name: "诊断中心" }),
    ).toBeInTheDocument()
    expect(screen.getByText("平台 readiness、组件状态和租户配置诊断")).toBeInTheDocument()
    expect(screen.getByText(/日志检索、测试链接触发/)).toBeInTheDocument()
    expect(screen.queryByText("Console 退出关系")).not.toBeInTheDocument()
    expect(
      screen.queryByText(/返回 Console|使用 Console|Console 兜底/),
    ).not.toBeInTheDocument()
  }, 20000)

  it.each([
    ["/enterprise-admin/quota", "配额管理", "Token 用量、默认限额和超限审计只读视图"],
    ["/enterprise-admin/security", "安全中心", "策略基线、权限拒绝审计与安全治理入口"],
    ["/enterprise-admin/backups", "备份恢复", "备份列表、生产策略和恢复演练"],
  ])("renders %s route", async (pathname, heading, description) => {
    const { default: App } = await importApp(pathname)

    render(<App />)

    expect(
      await screen.findByRole("heading", { name: heading }),
    ).toBeInTheDocument()
    expect(screen.getByText(description)).toBeInTheDocument()
  }, 20000)

  it("renders metrics route with readonly observability summary", async () => {
    const { default: App } = await importApp("/enterprise-admin/metrics")

    render(<App />)

    expect(
      await screen.findByRole("heading", { name: "指标监控" }),
    ).toBeInTheDocument()
    expect(
      screen.getByText("Prometheus 指标只读摘要和原始预览"),
    ).toBeInTheDocument()
    expect(
      screen.getByText("告警/趋势/导出/跨租户下钻阶段化开放"),
    ).toBeInTheDocument()
    expect(screen.queryByText("Phase 3/4 后续增强")).not.toBeInTheDocument()
  }, 20000)

  it("blocks tenant admin from platform-only routes", async () => {
    const authApi = await import("@/api/auth")
    vi.mocked(authApi.getAuthStatus).mockResolvedValueOnce({
      authenticated: true,
      username: "tenant-admin",
      role: "tenant_admin",
    })

    const { default: App } = await importApp("/enterprise-admin/security")

    render(<App />)

    expect(
      await screen.findByRole("heading", { name: "无权访问" }),
    ).toBeInTheDocument()
    expect(screen.getByText(/当前角色无权访问该模块/)).toBeInTheDocument()
  }, 20000)

  it("renders settings route with system settings MVP", async () => {
    const { default: App } = await importApp("/enterprise-admin/settings")

    render(<App />)

    expect(
      await screen.findByRole("heading", { name: "系统设置" }),
    ).toBeInTheDocument()
    expect(screen.getByText("平台级只读设置摘要与合规导出")).toBeInTheDocument()
    expect(screen.queryByText("Phase 3/4 后续增强")).not.toBeInTheDocument()
    expect(screen.queryByText("未开放")).not.toBeInTheDocument()
    expect(
      screen.queryByText(/返回 Console|使用 Console|Console 兜底/),
    ).not.toBeInTheDocument()
  }, 20000)

  it("blocks tenant admin from settings route", async () => {
    const authApi = await import("@/api/auth")
    vi.mocked(authApi.getAuthStatus).mockResolvedValueOnce({
      authenticated: true,
      username: "tenant-admin",
      role: "tenant_admin",
    })

    const { default: App } = await importApp("/enterprise-admin/settings")

    render(<App />)

    expect(
      await screen.findByRole("heading", { name: "无权访问" }),
    ).toBeInTheDocument()
    expect(screen.getByText(/当前角色无权访问该模块/)).toBeInTheDocument()
  }, 20000)
})
