import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import {
  listPermissionDenials,
  listTenantPolicies,
  putTenantPolicy,
} from "@/api/security"
import SecurityPage from "./SecurityPage"

vi.mock("@/api/security", () => ({
  listPermissionDenials: vi.fn(),
  listTenantPolicies: vi.fn(),
  putTenantPolicy: vi.fn(),
}))

const policy = {
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
}

describe("SecurityPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(listTenantPolicies).mockResolvedValue({ policies: [policy] })
    vi.mocked(listPermissionDenials).mockResolvedValue({
      events: [
        {
          id: "audit-deny-1",
          event_type: "authz.denied",
          action: "tenant:update",
          outcome: "denied",
          tenant_id: "acme",
          actor_id: "bob",
          resource_type: "tenant",
          resource_id: "wx_other",
          created_at: "2026-05-16T00:00:00+00:00",
        },
      ],
      count: 1,
    })
    vi.mocked(putTenantPolicy).mockResolvedValue({
      ...policy,
      token_quota_monthly: 5000,
    })
  })

  it("renders policies and permission-denial review", async () => {
    render(<SecurityPage />)

    expect(
      await screen.findByRole("heading", { name: "安全中心" }),
    ).toBeInTheDocument()
    expect(screen.getByText("默认成员策略")).toBeInTheDocument()
    expect(screen.getByText("tenant:update")).toBeInTheDocument()
    expect(screen.queryByText("authz.denied")).not.toBeInTheDocument()
    expect(screen.getByLabelText("default 月 Token 配额")).toBeInTheDocument()
    expect(
      screen.getAllByText(/审批处置、blocked history 清理/).length,
    ).toBeGreaterThan(0)
    expect(
      screen.queryByRole("button", { name: /审批|处置|清理|blocked history/ }),
    ).not.toBeInTheDocument()
  })

  it("saves audited tenant policy quota field", async () => {
    render(<SecurityPage />)

    await userEvent.type(
      await screen.findByLabelText("default 月 Token 配额"),
      "5000",
    )
    await userEvent.click(screen.getByRole("button", { name: /保.*存/ }))

    await waitFor(() => {
      expect(putTenantPolicy).toHaveBeenCalledWith("default", {
        ...policy,
        token_quota_monthly: 5000,
      })
    })
  })
})
