import { del, get, put } from "./http"
import type {
  SystemPromptFilesResponse,
  TenantSecuritySettings,
  TenantTemplate,
  TenantTemplateListResponse,
} from "./types"

const TENANT_BASE = "/config/channels/wecom_tenant/tenants"
const TEMPLATE_BASE = "/platform/tenancy/templates"

function tenantConfigBase(agentId: string): string {
  return `${TENANT_BASE}/${encodeURIComponent(agentId)}`
}

export function listTenantTemplates(): Promise<TenantTemplateListResponse> {
  return get<TenantTemplateListResponse>(TEMPLATE_BASE)
}

export function upsertTenantTemplate(
  templateId: string,
  payload: TenantTemplate,
): Promise<TenantTemplate> {
  return put<TenantTemplate>(`${TEMPLATE_BASE}/${encodeURIComponent(templateId)}`, payload)
}

export function deleteTenantTemplate(
  templateId: string,
): Promise<{ deleted: boolean }> {
  return del<{ deleted: boolean }>(`${TEMPLATE_BASE}/${encodeURIComponent(templateId)}`)
}

export function getTenantSystemPrompts(
  agentId: string,
): Promise<SystemPromptFilesResponse> {
  return get<SystemPromptFilesResponse>(`${tenantConfigBase(agentId)}/system-prompts`)
}

export function putTenantSystemPrompts(
  agentId: string,
  payload: SystemPromptFilesResponse,
): Promise<SystemPromptFilesResponse> {
  return put<SystemPromptFilesResponse>(
    `${tenantConfigBase(agentId)}/system-prompts`,
    payload,
  )
}

export function getTenantSecuritySettings(
  agentId: string,
): Promise<TenantSecuritySettings> {
  return get<TenantSecuritySettings>(`${tenantConfigBase(agentId)}/security`)
}

export function putTenantSecuritySettings(
  agentId: string,
  payload: TenantSecuritySettings,
): Promise<TenantSecuritySettings> {
  return put<TenantSecuritySettings>(`${tenantConfigBase(agentId)}/security`, payload)
}
