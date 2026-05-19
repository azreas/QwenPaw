import { get, post } from "./http"
import type {
  TenantCronJob,
  TenantHealthResponse,
  TenantRuntimeFileListResponse,
} from "./types"

const TENANT_BASE = "/config/channels/wecom_tenant/tenants"

function tenantRuntimeBase(agentId: string): string {
  return `${TENANT_BASE}/${encodeURIComponent(agentId)}`
}

function cronJobUrl(agentId: string, jobId: string, action?: "pause" | "resume" | "run"): string {
  const base = `${tenantRuntimeBase(agentId)}/cron/${encodeURIComponent(jobId)}`
  return action ? `${base}/${action}` : base
}

export function getTenantHealth(agentId: string): Promise<TenantHealthResponse> {
  return get<TenantHealthResponse>(`${tenantRuntimeBase(agentId)}/health`)
}

export function listTenantWorkspaceFiles(
  agentId: string,
): Promise<TenantRuntimeFileListResponse> {
  return get<TenantRuntimeFileListResponse>(`${tenantRuntimeBase(agentId)}/files`)
}

export function listTenantMemoryFiles(
  agentId: string,
): Promise<TenantRuntimeFileListResponse> {
  return get<TenantRuntimeFileListResponse>(`${tenantRuntimeBase(agentId)}/memory`)
}

export function listTenantCronJobs(agentId: string): Promise<TenantCronJob[]> {
  return get<TenantCronJob[]>(`${tenantRuntimeBase(agentId)}/cron`)
}

export function pauseTenantCronJob(agentId: string, jobId: string): Promise<{ paused: boolean }> {
  return post<{ paused: boolean }>(cronJobUrl(agentId, jobId, "pause"))
}

export function resumeTenantCronJob(agentId: string, jobId: string): Promise<{ resumed: boolean }> {
  return post<{ resumed: boolean }>(cronJobUrl(agentId, jobId, "resume"))
}

export function runTenantCronJob(agentId: string, jobId: string): Promise<{ started: boolean }> {
  return post<{ started: boolean }>(cronJobUrl(agentId, jobId, "run"))
}
