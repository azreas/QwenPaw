import { get, put } from "./http"
import type { AgentsLLMRoutingConfig, ModelSlotConfig } from "./types"

const TENANT_BASE = "/config/channels/wecom_tenant/tenants"

function tenantModelBase(agentId: string): string {
  return `${TENANT_BASE}/${encodeURIComponent(agentId)}`
}

export function getTenantModel(agentId: string): Promise<ModelSlotConfig | null> {
  return get<ModelSlotConfig | null>(`${tenantModelBase(agentId)}/model`)
}

export function putTenantModel(
  agentId: string,
  payload: ModelSlotConfig,
): Promise<ModelSlotConfig> {
  return put<ModelSlotConfig>(`${tenantModelBase(agentId)}/model`, payload)
}

export function getTenantLlmRouting(agentId: string): Promise<AgentsLLMRoutingConfig> {
  return get<AgentsLLMRoutingConfig>(`${tenantModelBase(agentId)}/llm-routing`)
}

export function putTenantLlmRouting(
  agentId: string,
  payload: AgentsLLMRoutingConfig,
): Promise<AgentsLLMRoutingConfig> {
  return put<AgentsLLMRoutingConfig>(
    `${tenantModelBase(agentId)}/llm-routing`,
    payload,
  )
}
