import { getEnterpriseReadiness, getReady } from "./runtime"
import { diagnoseTenantEntryConfig } from "./entryConfig"
import { getTenantHealth } from "./tenantRuntime"
import type {
  EnterpriseReadiness,
  ReadyStatus,
  TenantEntryDiagnostics,
  TenantHealthResponse,
} from "./types"

export interface DiagnosticsOverview {
  ready: ReadyStatus
  enterprise: EnterpriseReadiness
}

export interface TenantDiagnosticsSnapshot {
  health: TenantHealthResponse
  entry: TenantEntryDiagnostics
}

export async function getDiagnosticsOverview(): Promise<DiagnosticsOverview> {
  const [ready, enterprise] = await Promise.all([
    getReady(),
    getEnterpriseReadiness(),
  ])
  return { ready, enterprise }
}

export async function getTenantDiagnosticsSnapshot(
  agentId: string,
): Promise<TenantDiagnosticsSnapshot> {
  const [health, entry] = await Promise.all([
    getTenantHealth(agentId),
    diagnoseTenantEntryConfig(agentId),
  ])
  return { health, entry }
}
