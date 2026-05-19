import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { message } from "antd"
import BusinessTracePage from "./BusinessTracePage"
import { listBusinessCalls } from "@/api/audit"
import { listWecomTenants } from "@/api/tenants"
import {
  getOpsOverview,
  getTenantOpsSummary,
  markTenantBadCase,
} from "@/api/ops"
import { ApiError } from "@/api/http"

vi.mock("@/api/tenants", () => ({
  listWecomTenants: vi.fn(),
}))

vi.mock("@/api/ops", () => ({
  getOpsOverview: vi.fn(),
  getTenantOpsSummary: vi.fn(),
  markTenantBadCase: vi.fn(),
}))

vi.mock("@/api/audit", () => ({
  listBusinessCalls: vi.fn(),
}))

const messageErrorSpy = vi.spyOn(message, "error").mockImplementation(() => {
  const close = () => undefined
  return close as never
})

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
} as const

const overview = {
  total_tenants: 2,
  running_tenants: 1,
  unhealthy_tenants: 0,
  business_calls_24h: 20,
  failed_calls_24h: 2,
  failure_rate: 0.1,
  entrypoints: { webchat: 12, wecom: 8 },
  top_failed_abilities: [],
}

const summary = {
  tenant_id: "acme",
  agent_id: "wx_acme",
  health_status: "healthy",
  last_activity_at: "2026-05-13T09:30:00+00:00",
  business_calls_24h: 12,
  failed_calls_24h: 1,
  recent_failures: [],
}

const traces = [
  {
    id: "trace-1",
    tenant_id: "acme",
    agent_id: "wx_acme",
    session_id: "session-1",
    actor_id: "user-1",
    entrypoint: "webchat",
    ability_type: "skill",
    ability_name: "sales_report",
    call_type: "skill",
    call_name: "sales_report",
    duration_ms: 321,
    status: "success",
    error_code: "",
    error_reason: "",
    request_id: "req-1",
    trace_id: "trace-req-1",
    created_at: "2026-05-13T09:00:00+00:00",
  },
] as const

const failureTrace = {
  id: "trace-2",
  tenant_id: "acme",
  agent_id: "wx_acme",
  session_id: "session-2",
  actor_id: "user-2",
  entrypoint: "wecom",
  ability_type: "mcp",
  ability_name: "erp",
  call_type: "mcp",
  call_name: "erp",
  duration_ms: 1200,
  status: "timeout",
  error_code: "mcp.timeout",
  error_reason: "timeout",
  request_id: "req-2",
  trace_id: "trace-req-2",
  created_at: "2026-05-13T09:10:00+00:00",
} as const

describe("BusinessTracePage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    messageErrorSpy.mockClear()
    vi.mocked(listWecomTenants).mockResolvedValue({ tenants: [tenant] })
    vi.mocked(getOpsOverview).mockResolvedValue(overview)
    vi.mocked(getTenantOpsSummary).mockResolvedValue(summary)
    vi.mocked(listBusinessCalls).mockResolvedValue({
      items: [...traces, failureTrace],
      total: traces.length + 1,
    })
  })

  it("renders overview stats and trace table", async () => {
    render(<BusinessTracePage />)

    expect(
      await screen.findByRole("heading", { name: "业务追踪" }),
    ).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: "业务调用" })).toHaveAttribute(
      "aria-selected",
      "true",
    )
    expect(screen.getByRole("tab", { name: "审计日志" })).toBeInTheDocument()
    expect(await screen.findByText("租户总数")).toBeInTheDocument()
    expect(screen.getByText("运行中租户")).toBeInTheDocument()
    expect(screen.getByText("24h 调用")).toBeInTheDocument()
    expect(screen.getByText("24h 失败")).toBeInTheDocument()
    expect(screen.getByText("失败率")).toBeInTheDocument()
    expect(await screen.findByText("sales_report")).toBeInTheDocument()
    expect(await screen.findByText("erp")).toBeInTheDocument()
    expect(screen.getByText("MCP")).toBeInTheDocument()
    expect(screen.getByText("mcp.timeout")).toBeInTheDocument()
    expect(screen.getByText("req-1")).toBeInTheDocument()
    expect(screen.getByText("trace-req-1")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "标记 trace-2" })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "标记 trace-1" })).not.toBeInTheDocument()
  })

  it("shows staged audit log guidance in audit log tab", async () => {
    render(<BusinessTracePage />)

    await screen.findByRole("heading", { name: "业务追踪" })
    await userEvent.click(screen.getByRole("tab", { name: "审计日志" }))

    expect(
      await screen.findByText(/通用审计日志搜索、权限拒绝事件、导出和保存筛选/),
    ).toBeInTheDocument()
  })

  it("queries traces with filters from form", async () => {
    render(<BusinessTracePage />)

    await screen.findByRole("heading", { name: "业务追踪" })
    await userEvent.click(screen.getByLabelText("调用类型"))
    const skillOptions = await screen.findAllByText("Skill")
    await userEvent.click(skillOptions[skillOptions.length - 1])
    await userEvent.type(screen.getByLabelText("调用名称"), "sales_report")
    await userEvent.type(screen.getByLabelText("错误码"), "policy.denied")
    await userEvent.type(screen.getByLabelText("Request ID"), "req-1")
    await userEvent.type(screen.getByLabelText("Trace ID"), "trace-1")
    await userEvent.click(screen.getByRole("button", { name: /查.*询/ }))

    await waitFor(() => {
      expect(listBusinessCalls).toHaveBeenLastCalledWith({
        agent_id: "wx_acme",
        call_type: "skill",
        call_name: "sales_report",
        error_code: "policy.denied",
        request_id: "req-1",
        trace_id: "trace-1",
        limit: 100,
      })
    })
  })

  it("does not load tenant summary or traces when tenant list is empty", async () => {
    vi.mocked(listWecomTenants).mockResolvedValue({ tenants: [] })

    render(<BusinessTracePage />)

    expect(await screen.findByText("暂无租户")).toBeInTheDocument()
    expect(getTenantOpsSummary).not.toHaveBeenCalled()
    expect(listBusinessCalls).not.toHaveBeenCalled()
  })

  it("shows forbidden message when trace access is denied", async () => {
    vi.mocked(listBusinessCalls).mockRejectedValue(
      new ApiError("forbidden", 403),
    )

    render(<BusinessTracePage />)

    await waitFor(() => {
      expect(messageErrorSpy).toHaveBeenCalledWith(
        "当前身份无权查看业务追踪或未绑定租户",
      )
    })
  })

  it("marks failed trace as bad case", async () => {
    vi.mocked(markTenantBadCase).mockResolvedValue({
      case_id: "case-trace-2",
      source_audit_id: "trace-2",
      source_request_id: "req-2",
      source_trace_id: "trace-req-2",
      category: "platform_runtime",
      status: "open",
      owner: "ops-team",
      note: "timeout needs investigation",
      ability_type: "mcp",
      ability_name: "erp",
      entrypoint: "wecom",
      created_at: "2026-05-13T09:10:00+00:00",
      updated_at: "2026-05-13T09:10:00+00:00",
    })

    render(<BusinessTracePage />)

    await userEvent.click(await screen.findByRole("button", { name: "标记 trace-2" }))
    expect(screen.getByLabelText("备注")).toHaveValue("timeout")
    await userEvent.type(screen.getByLabelText("负责人"), "ops-team")
    await userEvent.clear(screen.getByLabelText("备注"))
    await userEvent.type(screen.getByLabelText("备注"), "timeout needs investigation")
    await userEvent.click(screen.getByRole("button", { name: "确认标记" }))

    await waitFor(() => {
      expect(markTenantBadCase).toHaveBeenCalledWith("wx_acme", {
        source_audit_id: "trace-2",
        source_request_id: "req-2",
        source_trace_id: "trace-req-2",
        category: "platform_runtime",
        owner: "ops-team",
        note: "timeout needs investigation",
      })
    })
  })

  it("shows duplicate bad case message for 409", async () => {
    vi.mocked(markTenantBadCase).mockRejectedValue(
      new ApiError("already exists", 409),
    )

    render(<BusinessTracePage />)

    await userEvent.click(await screen.findByRole("button", { name: "标记 trace-2" }))
    await userEvent.click(screen.getByRole("button", { name: "确认标记" }))

    await waitFor(() => {
      expect(messageErrorSpy).toHaveBeenCalledWith("该调用已标记为 Bad Case")
    })
  })

  it("shows not persisted message for 503", async () => {
    vi.mocked(markTenantBadCase).mockRejectedValue(
      new ApiError("Audit service unavailable", 503),
    )

    render(<BusinessTracePage />)

    await userEvent.click(await screen.findByRole("button", { name: "标记 trace-2" }))
    await userEvent.click(screen.getByRole("button", { name: "确认标记" }))

    await waitFor(() => {
      expect(messageErrorSpy).toHaveBeenCalledWith("审计服务不可用，Bad Case 未保存")
    })
  })

  it("does not show internal page completeness details", async () => {
    render(<BusinessTracePage />)

    expect(await screen.findByRole("heading", { name: "业务追踪" })).toBeInTheDocument()
    expect(screen.queryByText("页面完整性")).not.toBeInTheDocument()
    expect(screen.queryByText("Console 退出关系")).not.toBeInTheDocument()
  })
})
