import { del, get, put } from "./http"
import type {
  DeleteResponse,
  PlatformTenantListResponse,
  TenantPolicy,
  TenantPolicyListResponse,
  TenantTemplate,
  TenantTemplateListResponse,
} from "./types"

const POLICY_BASE = "/platform/tenancy/policies"
const TEMPLATE_BASE = "/platform/tenancy/templates"
const TENANT_BASE = "/platform/tenancy/tenants"

export function listPolicies(): Promise<TenantPolicyListResponse> {
  return get<TenantPolicyListResponse>(POLICY_BASE)
}

export function savePolicy(
  policyId: string,
  payload: TenantPolicy,
): Promise<TenantPolicy> {
  return put<TenantPolicy>(`${POLICY_BASE}/${encodeURIComponent(policyId)}`, payload)
}

export function deletePolicy(policyId: string): Promise<DeleteResponse> {
  return del<DeleteResponse>(`${POLICY_BASE}/${encodeURIComponent(policyId)}`)
}

export function listTemplates(): Promise<TenantTemplateListResponse> {
  return get<TenantTemplateListResponse>(TEMPLATE_BASE)
}

export function saveTemplate(
  templateId: string,
  payload: TenantTemplate,
): Promise<TenantTemplate> {
  return put<TenantTemplate>(
    `${TEMPLATE_BASE}/${encodeURIComponent(templateId)}`,
    payload,
  )
}

export function deleteTemplate(templateId: string): Promise<DeleteResponse> {
  return del<DeleteResponse>(`${TEMPLATE_BASE}/${encodeURIComponent(templateId)}`)
}

export function listPlatformTenants(): Promise<PlatformTenantListResponse> {
  return get<PlatformTenantListResponse>(TENANT_BASE)
}
