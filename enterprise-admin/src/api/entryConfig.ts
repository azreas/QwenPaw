import { get, post, put } from "./http"
import type { TenantEntryConfig, TenantEntryDiagnostics } from "./types"

const TENANT_BASE = "/config/channels/wecom_tenant/tenants"

function entryConfigBase(agentId: string): string {
  return `${TENANT_BASE}/${encodeURIComponent(agentId)}/entry-config`
}

export function getTenantEntryConfig(
  agentId: string,
): Promise<TenantEntryConfig> {
  return get<TenantEntryConfig>(entryConfigBase(agentId))
}

export function putTenantEntryConfig(
  agentId: string,
  payload: TenantEntryConfig,
): Promise<TenantEntryConfig> {
  return put<TenantEntryConfig>(entryConfigBase(agentId), payload)
}

export function diagnoseTenantEntryConfig(
  agentId: string,
): Promise<TenantEntryDiagnostics> {
  return post<TenantEntryDiagnostics>(`${entryConfigBase(agentId)}/diagnose`)
}
