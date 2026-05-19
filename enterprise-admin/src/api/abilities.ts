import { del, get, patch, post, put } from "./http"
import type {
  MCPClientConfig,
  MCPCreateRequest,
  MCPClientInfo,
  MCPConnectionTestResponse,
  MessageResponse,
  SkillInstallRequest,
  SkillInfo,
  SkillOperationResponse,
  ToolAsyncExecutionRequest,
  ToolInfo,
} from "./types"

const TENANT_BASE = "/config/channels/wecom_tenant/tenants"

function tenantAbilityBase(agentId: string): string {
  return `${TENANT_BASE}/${encodeURIComponent(agentId)}`
}

export function listTenantSkills(agentId: string): Promise<SkillInfo[]> {
  return get<SkillInfo[]>(`${tenantAbilityBase(agentId)}/skills`)
}

export function toggleTenantSkill(
  agentId: string,
  skillId: string,
): Promise<SkillOperationResponse> {
  return patch<SkillOperationResponse>(
    `${tenantAbilityBase(agentId)}/skills/${encodeURIComponent(skillId)}/toggle`,
  )
}

export function installTenantSkill(
  agentId: string,
  payload: SkillInstallRequest,
): Promise<SkillOperationResponse> {
  return post<SkillOperationResponse>(`${tenantAbilityBase(agentId)}/skills/install`, payload)
}

export function deleteTenantSkill(
  agentId: string,
  skillId: string,
): Promise<SkillOperationResponse> {
  return del<SkillOperationResponse>(
    `${tenantAbilityBase(agentId)}/skills/${encodeURIComponent(skillId)}`,
  )
}

export function listTenantTools(agentId: string): Promise<ToolInfo[]> {
  return get<ToolInfo[]>(`${tenantAbilityBase(agentId)}/tools`)
}

export function toggleTenantTool(agentId: string, toolName: string): Promise<ToolInfo> {
  return patch<ToolInfo>(
    `${tenantAbilityBase(agentId)}/tools/${encodeURIComponent(toolName)}/toggle`,
  )
}

export function updateTenantToolAsyncExecution(
  agentId: string,
  toolName: string,
  payload: ToolAsyncExecutionRequest,
): Promise<ToolInfo> {
  return patch<ToolInfo>(
    `${tenantAbilityBase(agentId)}/tools/${encodeURIComponent(toolName)}/async-execution`,
    payload,
  )
}

export function listTenantMcpClients(agentId: string): Promise<MCPClientInfo[]> {
  return get<MCPClientInfo[]>(`${tenantAbilityBase(agentId)}/mcp`)
}

export function toggleTenantMcpClient(
  agentId: string,
  clientKey: string,
): Promise<MCPClientInfo> {
  return patch<MCPClientInfo>(
    `${tenantAbilityBase(agentId)}/mcp/${encodeURIComponent(clientKey)}/toggle`,
  )
}

export function createTenantMcpClient(
  agentId: string,
  payload: MCPCreateRequest,
): Promise<MCPClientInfo> {
  return post<MCPClientInfo>(`${tenantAbilityBase(agentId)}/mcp`, payload)
}

export function updateTenantMcpClient(
  agentId: string,
  clientKey: string,
  payload: MCPClientConfig,
): Promise<MCPClientInfo> {
  return put<MCPClientInfo>(
    `${tenantAbilityBase(agentId)}/mcp/${encodeURIComponent(clientKey)}`,
    payload,
  )
}

export function deleteTenantMcpClient(
  agentId: string,
  clientKey: string,
): Promise<MessageResponse> {
  return del<MessageResponse>(
    `${tenantAbilityBase(agentId)}/mcp/${encodeURIComponent(clientKey)}`,
  )
}

export function testTenantMcpClient(
  agentId: string,
  clientKey: string,
): Promise<MCPConnectionTestResponse> {
  return post<MCPConnectionTestResponse>(
    `${tenantAbilityBase(agentId)}/mcp/${encodeURIComponent(clientKey)}/test`,
  )
}
