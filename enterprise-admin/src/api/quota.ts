import { get } from "./http"
import type {
  AuditEventListResponse,
  QuotaConfigSummary,
  TokenUsageRecord,
  TokenUsageSummary,
} from "./types"

export interface TokenUsageQuery {
  start_date?: string
  end_date?: string
  model?: string
  provider?: string
}

export function getTokenUsageSummary(
  query: TokenUsageQuery = {},
): Promise<TokenUsageSummary> {
  return get<TokenUsageSummary>("/token-usage", { params: query })
}

export function getTokenUsageDetails(
  query: TokenUsageQuery = {},
): Promise<TokenUsageRecord[]> {
  return get<TokenUsageRecord[]>("/token-usage/details", { params: query })
}

export function getQuotaConfigSummary(): Promise<QuotaConfigSummary> {
  return get<QuotaConfigSummary>("/quota/summary")
}

export function listQuotaAuditEvents(): Promise<AuditEventListResponse> {
  return get<AuditEventListResponse>("/audit/events", {
    params: {
      event_type: "quota.denied",
      limit: 20,
    },
  })
}
