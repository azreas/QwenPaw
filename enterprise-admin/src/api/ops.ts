import { get, patch, post } from "./http"
import type {
  BadCaseCreateRequest,
  BadCaseItem,
  BadCaseListResponse,
  BadCaseUpdateRequest,
  BusinessTraceListResponse,
  BusinessTraceQuery,
  OpsOverviewResponse,
  TenantOpsSummaryResponse,
} from "./types"

const WECOM_CONFIG_BASE = "/config/channels/wecom_tenant"

function tenantOpsBase(agentId: string): string {
  return `${WECOM_CONFIG_BASE}/tenants/${encodeURIComponent(agentId)}/ops`
}

function tenantBadCasesUrl(agentId: string): string {
  return `${WECOM_CONFIG_BASE}/tenants/${encodeURIComponent(agentId)}/bad-cases`
}

export function getOpsOverview(): Promise<OpsOverviewResponse> {
  return get<OpsOverviewResponse>(`${WECOM_CONFIG_BASE}/ops/overview`)
}

export function getTenantOpsSummary(
  agentId: string,
): Promise<TenantOpsSummaryResponse> {
  return get<TenantOpsSummaryResponse>(`${tenantOpsBase(agentId)}/summary`)
}

export function listTenantBusinessTraces(
  agentId: string,
  query: BusinessTraceQuery = {},
): Promise<BusinessTraceListResponse> {
  return get<BusinessTraceListResponse>(`${tenantOpsBase(agentId)}/traces`, {
    params: query,
  })
}

export function listTenantBadCases(
  agentId: string,
): Promise<BadCaseListResponse> {
  return get<BadCaseListResponse>(tenantBadCasesUrl(agentId))
}

export function markTenantBadCase(
  agentId: string,
  payload: BadCaseCreateRequest,
): Promise<BadCaseItem> {
  return post<BadCaseItem>(tenantBadCasesUrl(agentId), payload)
}

export function updateTenantBadCase(
  agentId: string,
  caseId: string,
  payload: BadCaseUpdateRequest,
): Promise<BadCaseItem> {
  return patch<BadCaseItem>(
    `${tenantBadCasesUrl(agentId)}/${encodeURIComponent(caseId)}`,
    payload,
  )
}
