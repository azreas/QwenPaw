import { render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import {
  getDiagnosticsOverview,
  getTenantDiagnosticsSnapshot,
} from "@/api/diagnostics"
import { listWecomTenants } from "@/api/tenants"
import DiagnosticsPage from "./DiagnosticsPage"

vi.mock("@/api/diagnostics", () => ({
  getDiagnosticsOverview: vi.fn(),
  getTenantDiagnosticsSnapshot: vi.fn(),
}))

vi.mock("@/api/tenants", () => ({
  listWecomTenants: vi.fn(),
}))

describe("DiagnosticsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(getDiagnosticsOverview).mockResolvedValue({
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
        ] as unknown as Record<string, unknown>,
      },
    })
    vi.mocked(listWecomTenants).mockResolvedValue({
      tenants: [
        {
          tenant_id: "acme",
          agent_id: "wx_acme",
          workspace_dir: "D:/tenants/wx_acme",
          exists: true,
          initialized: true,
          running: true,
          updated_at: "2026-05-16T00:00:00+00:00",
          chat_count: 1,
          job_count: 1,
          source: "workspace",
        },
      ],
    })
    vi.mocked(getTenantDiagnosticsSnapshot).mockResolvedValue({
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
    })
  })

  it("renders platform and tenant diagnostics", async () => {
    render(<DiagnosticsPage />)

    expect(
      await screen.findByRole("heading", { name: "诊断中心" }),
    ).toBeInTheDocument()
    expect(screen.getByText("repository unavailable")).toBeInTheDocument()
    expect(screen.getByText("authz")).toBeInTheDocument()
    await waitFor(() => {
      expect(getTenantDiagnosticsSnapshot).toHaveBeenCalledWith("wx_acme")
    })
    expect(
      screen.getByText((content) => content.includes("workspace_exists")),
    ).toBeInTheDocument()
    expect(
      screen.getByText("日志摘要与安全测试链接阶段化开放"),
    ).toBeInTheDocument()
  })

  it("does not render audit storage unavailable as a successful load", async () => {
    vi.mocked(getDiagnosticsOverview).mockResolvedValue({
      ready: {
        ready: true,
        components: [
          {
            name: "audit",
            status: "ok",
            message: "loaded",
          },
        ],
      },
      enterprise: {
        status: "ready",
        checks: [
          {
            name: "audit_storage",
            status: "pass",
            required: true,
            message: "storage unavailable",
          },
        ] as unknown as Record<string, unknown>,
      },
    })

    render(<DiagnosticsPage />)

    expect(await screen.findByText("audit_storage")).toBeInTheDocument()
    expect(screen.getByText("storage unavailable")).toBeInTheDocument()
    expect(screen.queryByText("pass")).not.toBeInTheDocument()
    expect(screen.getByText("fail")).toBeInTheDocument()
  })
})
