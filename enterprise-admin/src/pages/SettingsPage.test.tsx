import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import {
  exportComplianceAudit,
  getPlatformSettingsSummary,
} from "@/api/settings"
import SettingsPage from "./SettingsPage"

vi.mock("@/api/settings", () => ({
  exportComplianceAudit: vi.fn(),
  getPlatformSettingsSummary: vi.fn(),
}))

const summary: {
  frontend: {
    mode: string
    console_enabled: boolean
    root_entry: "enterprise-admin" | "console"
    console_access: "disabled" | "migration"
  }
  storage: {
    backend: string
    database_url_configured: boolean
    database_url_redacted: boolean
  }
  audit: {
    storage_available: boolean
    backend: string
  }
  compliance: {
    export_available: boolean
    formats: Array<"json" | "csv">
    reason: string
  }
  controlled_switches: Array<{
    key: string
    label: string
    status: string
    source: string
    online_edit_supported: boolean
    value_redacted: boolean
    reason: string
  }>
} = {
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
  controlled_switches: [
    {
      key: "frontend_mode",
      label: "默认管理入口",
      status: "enterprise-admin",
      source: "QWENPAW_FRONTEND_MODE",
      online_edit_supported: false,
      value_redacted: true,
      reason: "MVP only reports current state; online editing is unsupported.",
    },
  ],
}

describe("SettingsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(getPlatformSettingsSummary).mockResolvedValue(summary)
  })

  it("renders platform settings MVP without placeholder copy", async () => {
    render(<SettingsPage />)

    expect(
      await screen.findByRole("heading", { name: "系统设置" }),
    ).toBeInTheDocument()
    expect(screen.getByText("平台级只读设置摘要与合规导出")).toBeInTheDocument()
    expect(screen.getByText("sqlite")).toBeInTheDocument()
    expect(screen.getByText("QWENPAW_FRONTEND_MODE")).toBeInTheDocument()
    expect(screen.getByText(/在线修改不在本期范围/)).toBeInTheDocument()
    expect(screen.queryByText("未开放")).not.toBeInTheDocument()
    expect(screen.queryByText(/返回 Console|Console 兜底/)).not.toBeInTheDocument()
  })

  it("shows degraded state when summary fails", async () => {
    vi.mocked(getPlatformSettingsSummary).mockRejectedValue(new Error("boom"))

    render(<SettingsPage />)

    expect(await screen.findByText("设置摘要不可用")).toBeInTheDocument()
    expect(screen.getByText(/请稍后重试或查看诊断中心/)).toBeInTheDocument()
  })

  it("exports compliance audit with tenant as filter only", async () => {
    const user = userEvent.setup()
    vi.mocked(exportComplianceAudit).mockResolvedValue({
      blob: new Blob(["[]"], { type: "application/json" }),
      filename: "audit-export.json",
    })

    render(<SettingsPage />)

    await screen.findByRole("heading", { name: "系统设置" })
    await user.type(screen.getByLabelText("租户筛选"), "wx_acme")
    await user.click(screen.getByRole("button", { name: "导出审计" }))

    await waitFor(() => {
      expect(exportComplianceAudit).toHaveBeenCalledWith(
        expect.objectContaining({
          format: "json",
          tenant_id: "wx_acme",
          limit: 1000,
        }),
      )
    })
    expect(screen.getByText(/租户字段仅作为审计导出筛选/)).toBeInTheDocument()
    // 验证导出成功消息（下载逻辑在真实浏览器中生效）
    expect(screen.queryByText(/审计导出已下载|审计导出已生成/)).toBeInTheDocument()
  })

  it("shows export unavailable when compliance is degraded", async () => {
    vi.mocked(getPlatformSettingsSummary).mockResolvedValue({
      ...summary,
      audit: { storage_available: false, backend: "json" },
      compliance: {
        export_available: false,
        formats: ["json", "csv"],
        reason: "SQL audit storage required for compliance export",
      },
    })

    render(<SettingsPage />)

    expect(
      await screen.findByText("SQL audit storage required for compliance export"),
    ).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "导出审计" })).toBeDisabled()
  })
})
