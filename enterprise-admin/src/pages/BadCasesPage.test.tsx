import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { message } from "antd"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { ApiError } from "@/api/http"
import {
  listTenantBadCases,
  updateTenantBadCase,
} from "@/api/ops"
import { listWecomTenants } from "@/api/tenants"
import BadCasesPage from "./BadCasesPage"

vi.mock("@/api/tenants", () => ({
  listWecomTenants: vi.fn(),
}))

vi.mock("@/api/ops", () => ({
  listTenantBadCases: vi.fn(),
  updateTenantBadCase: vi.fn(),
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
}

const badCases = [
  {
    case_id: "case-audit-1",
    source_audit_id: "audit-1",
    source_request_id: "req-1",
    source_trace_id: "trace-1",
    category: "data_quality",
    status: "open",
    owner: "ops-a",
    note: "needs check",
    ability_type: "skill",
    ability_name: "sales_report",
    call_type: "skill",
    call_name: "sales_report",
    entrypoint: "webchat",
    created_at: "2026-05-13T08:00:00+00:00",
    updated_at: "2026-05-13T08:00:00+00:00",
  },
  {
    case_id: "case-audit-2",
    source_audit_id: "audit-2",
    source_request_id: "req-2",
    source_trace_id: "trace-2",
    category: "platform_runtime",
    status: "resolved",
    owner: "ops-b",
    note: "fixed",
    ability_type: "mcp",
    ability_name: "erp",
    call_type: "mcp",
    call_name: "erp",
    entrypoint: "wecom",
    created_at: "2026-05-13T09:00:00+00:00",
    updated_at: "2026-05-13T09:30:00+00:00",
  },
  {
    case_id: "case-audit-3",
    source_audit_id: "audit-3",
    source_request_id: "req-3",
    source_trace_id: "trace-3",
    category: "permission_config",
    status: "triaged",
    owner: "ops-c",
    note: "assigned",
    ability_type: "skill",
    ability_name: "profile_sync",
    call_type: "policy",
    call_name: "profile_sync_guard",
    entrypoint: "webchat",
    created_at: "2026-05-13T10:00:00+00:00",
    updated_at: "2026-05-13T10:30:00+00:00",
  },
]

describe("BadCasesPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    messageErrorSpy.mockClear()
    vi.mocked(listWecomTenants).mockResolvedValue({ tenants: [tenant] })
    vi.mocked(listTenantBadCases).mockResolvedValue({
      items: [...badCases],
      total: badCases.length,
    })
  })

  it("loads default tenant and renders stats and table", async () => {
    render(<BadCasesPage />)

    expect(
      await screen.findByRole("heading", { name: "Bad Case" }),
    ).toBeInTheDocument()
    expect(await screen.findByText("acme / wx_acme")).toBeInTheDocument()
    expect(screen.getByText("总数")).toBeInTheDocument()
    expect(screen.getByText("待处理")).toBeInTheDocument()
    expect(screen.getByText("已分诊")).toBeInTheDocument()
    expect(screen.getByText("已转交")).toBeInTheDocument()
    expect(screen.getByText("已解决")).toBeInTheDocument()
    expect(screen.getByText("已忽略")).toBeInTheDocument()
    expect(
      await screen.findByRole("row", { name: /case-audit-1/ }),
    ).toBeInTheDocument()
    expect(screen.getByText("sales_report")).toBeInTheDocument()
    expect(screen.getByText("Skill")).toBeInTheDocument()
    expect(screen.getByText("profile_sync_guard")).toBeInTheDocument()
    expect(screen.getByText("Policy")).toBeInTheDocument()
    expect(listTenantBadCases).toHaveBeenCalledWith("wx_acme")
  })

  it("filters by status locally", async () => {
    render(<BadCasesPage />)

    expect(
      await screen.findByRole("row", { name: /case-audit-1/ }),
    ).toBeInTheDocument()
    await userEvent.click(screen.getByRole("combobox", { name: "状态" }))
    const resolvedOptions = await screen.findAllByText("已解决")
    await userEvent.click(resolvedOptions[resolvedOptions.length - 1])

    expect(
      screen.queryByRole("row", { name: /case-audit-1/ }),
    ).not.toBeInTheDocument()
    expect(screen.getByRole("row", { name: /case-audit-2/ })).toBeInTheDocument()
    expect(listTenantBadCases).toHaveBeenCalledTimes(1)
  })

  it("filters by category locally", async () => {
    render(<BadCasesPage />)

    expect(
      await screen.findByRole("row", { name: /case-audit-1/ }),
    ).toBeInTheDocument()
    await userEvent.click(screen.getByRole("combobox", { name: "分类" }))
    const permissionOptions = await screen.findAllByText("权限配置")
    await userEvent.click(permissionOptions[permissionOptions.length - 1])

    expect(
      screen.queryByRole("row", { name: /case-audit-1/ }),
    ).not.toBeInTheDocument()
    expect(screen.getByRole("row", { name: /case-audit-3/ })).toBeInTheDocument()
    expect(listTenantBadCases).toHaveBeenCalledTimes(1)
  })

  it("saves edits from drawer and reloads bad cases", async () => {
    vi.mocked(updateTenantBadCase).mockResolvedValue({
      ...badCases[0],
      status: "triaged",
      category: "permission_config",
      owner: "ops-team",
      note: "assigned",
    })

    render(<BadCasesPage />)

    await userEvent.click(
      await screen.findByRole("button", { name: "编辑 case-audit-1" }),
    )
    const drawer = await screen.findByRole("dialog", { name: "编辑 Bad Case" })
    await userEvent.click(within(drawer).getByRole("combobox", { name: "状态" }))
    const triagedOptions = await screen.findAllByText("已分诊")
    await userEvent.click(triagedOptions[triagedOptions.length - 1])
    await userEvent.click(within(drawer).getByRole("combobox", { name: "分类" }))
    const permissionOptions = await screen.findAllByText("权限配置")
    await userEvent.click(permissionOptions[permissionOptions.length - 1])
    await userEvent.clear(within(drawer).getByLabelText("负责人"))
    await userEvent.type(within(drawer).getByLabelText("负责人"), "ops-team")
    await userEvent.clear(within(drawer).getByLabelText("备注"))
    await userEvent.type(within(drawer).getByLabelText("备注"), "assigned")
    await userEvent.click(within(drawer).getByRole("button", { name: /保.*存/ }))

    await waitFor(() => {
      expect(updateTenantBadCase).toHaveBeenCalledWith(
        "wx_acme",
        "case-audit-1",
        {
          status: "triaged",
          category: "permission_config",
          owner: "ops-team",
          note: "assigned",
        },
      )
    })
    expect(listTenantBadCases).toHaveBeenCalledTimes(2)
  })

  it("does not load bad cases when tenant list is empty", async () => {
    vi.mocked(listWecomTenants).mockResolvedValue({ tenants: [] })

    render(<BadCasesPage />)

    expect(await screen.findByText("暂无租户")).toBeInTheDocument()
    expect(listTenantBadCases).not.toHaveBeenCalled()
  })

  it("shows not persisted message when update returns 503", async () => {
    vi.mocked(updateTenantBadCase).mockRejectedValue(
      new ApiError("Audit service unavailable", 503),
    )

    render(<BadCasesPage />)

    await userEvent.click(
      await screen.findByRole("button", { name: "编辑 case-audit-1" }),
    )
    const drawer = await screen.findByRole("dialog", { name: "编辑 Bad Case" })
    await userEvent.click(within(drawer).getByRole("button", { name: /保.*存/ }))

    await waitFor(() => {
      expect(messageErrorSpy).toHaveBeenCalledWith(
        "审计服务不可用，Bad Case 未保存",
      )
    })
  })

  it("does not show internal page completeness details", async () => {
    render(<BadCasesPage />)

    expect(await screen.findByRole("heading", { name: "Bad Case" })).toBeInTheDocument()
    expect(screen.queryByText("页面完整性")).not.toBeInTheDocument()
    expect(screen.queryByText("Console 退出关系")).not.toBeInTheDocument()
  })

  it("shows staged evidence, SLA and batch assignment notes", async () => {
    render(<BadCasesPage />)

    expect(await screen.findByText(/证据详情/)).toBeInTheDocument()
    expect(screen.getByText(/SLA/)).toBeInTheDocument()
    expect(screen.getByText(/批量分派/)).toBeInTheDocument()
  })
})
