import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import {
  getQuotaConfigSummary,
  getTokenUsageDetails,
  getTokenUsageSummary,
  listQuotaAuditEvents,
} from "@/api/quota"
import QuotaPage from "./QuotaPage"

vi.mock("@/api/quota", () => ({
  getQuotaConfigSummary: vi.fn(),
  getTokenUsageDetails: vi.fn(),
  getTokenUsageSummary: vi.fn(),
  listQuotaAuditEvents: vi.fn(),
}))

describe("QuotaPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(getTokenUsageSummary).mockResolvedValue({
      total_prompt_tokens: 100,
      total_completion_tokens: 50,
      total_calls: 3,
      by_date: {
        "2026-05-16": {
          prompt_tokens: 100,
          completion_tokens: 50,
          call_count: 3,
        },
      },
    })
    vi.mocked(getTokenUsageDetails).mockResolvedValue([
      {
        date: "2026-05-16",
        provider_id: "dashscope",
        model: "qwen-max",
        agent_id: "wx_acme",
        prompt_tokens: 100,
        completion_tokens: 50,
        call_count: 3,
      },
    ])
    vi.mocked(getQuotaConfigSummary).mockResolvedValue({
      enabled: true,
      redis_url_set: false,
      default_limits: [
        {
          dimension: "llm.token",
          window: "day",
          max_value: 1000000,
          resource: "*",
        },
      ],
    })
    vi.mocked(listQuotaAuditEvents).mockResolvedValue({
      events: [
        {
          id: "audit-1",
          event_type: "quota.denied",
          action: "consume_llm_tokens",
          outcome: "denied",
          tenant_id: "acme",
          resource_id: "llm.token",
          created_at: "2026-05-16T00:00:00+00:00",
        },
      ],
      count: 1,
    })
  })

  it("renders token usage, default quota and quota audit", async () => {
    render(<QuotaPage />)

    expect(
      await screen.findByRole("heading", { name: "配额管理" }),
    ).toBeInTheDocument()
    expect(screen.getByText("Prompt Tokens")).toBeInTheDocument()
    expect(screen.getByText("Completion Tokens")).toBeInTheDocument()
    expect(screen.getByText("已启用")).toBeInTheDocument()
    expect(screen.getByText("Redis 未配置")).toBeInTheDocument()
    expect(screen.getByText("qwen-max")).toBeInTheDocument()
    expect(screen.getByText("quota.denied")).toBeInTheDocument()
    expect(
      screen.getAllByText(/配额调整、超限处置和告警策略/).length,
    ).toBeGreaterThan(0)
    expect(
      screen.queryByRole("button", { name: /保存|调整|处置|告警策略/ }),
    ).not.toBeInTheDocument()
  })
})
