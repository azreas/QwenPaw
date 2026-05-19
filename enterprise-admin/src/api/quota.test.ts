import { beforeEach, describe, expect, it, vi } from "vitest"
import { get } from "./http"
import {
  getQuotaConfigSummary,
  getTokenUsageDetails,
  getTokenUsageSummary,
  listQuotaAuditEvents,
} from "./quota"

vi.mock("./http", () => ({
  get: vi.fn(),
}))

describe("quota api", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(get).mockResolvedValue({})
  })

  it("loads token usage summary and details with query params", async () => {
    await getTokenUsageSummary({ model: "qwen-max", provider: "dashscope" })
    await getTokenUsageDetails({ start_date: "2026-05-01" })

    expect(get).toHaveBeenNthCalledWith(1, "/token-usage", {
      params: { model: "qwen-max", provider: "dashscope" },
    })
    expect(get).toHaveBeenNthCalledWith(2, "/token-usage/details", {
      params: { start_date: "2026-05-01" },
    })
  })

  it("loads quota summary and quota audit events", async () => {
    await getQuotaConfigSummary()
    await listQuotaAuditEvents()

    expect(get).toHaveBeenNthCalledWith(1, "/quota/summary")
    expect(get).toHaveBeenNthCalledWith(2, "/audit/events", {
      params: {
        event_type: "quota.denied",
        limit: 20,
      },
    })
  })
})
