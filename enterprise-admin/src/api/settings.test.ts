import { beforeEach, describe, expect, it, vi } from "vitest"
import axios from "axios"
import {
  exportComplianceAudit,
  extractDownloadFilename,
  getPlatformSettingsSummary,
} from "./settings"
import { get } from "./http"

vi.mock("./http", () => ({
  get: vi.fn(),
}))

vi.mock("axios", () => ({
  default: {
    request: vi.fn(),
  },
}))

describe("settings api", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("loads protected platform settings summary", async () => {
    vi.mocked(get).mockResolvedValue({
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
    })

    await getPlatformSettingsSummary()

    expect(get).toHaveBeenCalledWith("/settings/platform-summary")
  })

  it("exports compliance audit as blob with filters", async () => {
    const blob = new Blob(["id,event_type"], { type: "text/csv" })
    vi.mocked(axios.request).mockResolvedValue({
      data: blob,
      headers: { "content-disposition": 'attachment; filename="audit-export.csv"' },
    })

    const result = await exportComplianceAudit({
      format: "csv",
      limit: 100,
      tenant_id: "wx_acme",
      event_type: "compliance.exported",
      start_time: "2026-05-18T00:00:00+00:00",
      end_time: "2026-05-18T23:59:59+00:00",
    })

    expect(axios.request).toHaveBeenCalledWith({
      method: "POST",
      url: "/api/compliance/audit/export",
      data: {
        format: "csv",
        limit: 100,
        tenant_id: "wx_acme",
        event_type: "compliance.exported",
        start_time: "2026-05-18T00:00:00+00:00",
        end_time: "2026-05-18T23:59:59+00:00",
      },
      responseType: "blob",
      headers: {
        Authorization: expect.any(String),
      },
    })
    expect(result.blob).toBe(blob)
    expect(result.filename).toBe("audit-export.csv")
  })

  it("extracts filename from content disposition with fallback", () => {
    expect(
      extractDownloadFilename('attachment; filename="audit-export.csv"', "json"),
    ).toBe("audit-export.csv")
    expect(extractDownloadFilename("", "csv")).toBe("audit-export.csv")
    expect(extractDownloadFilename("", "json")).toBe("audit-export.json")
  })
})
