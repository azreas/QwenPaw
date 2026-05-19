import { get, put } from "./http"
import type {
  AuditEventListResponse,
  TenantPolicy,
  TenantPolicyListResponse,
} from "./types"

export function listTenantPolicies(): Promise<TenantPolicyListResponse> {
  return get<TenantPolicyListResponse>("/platform/tenancy/policies")
}

export function putTenantPolicy(
  policyId: string,
  payload: TenantPolicy,
): Promise<TenantPolicy> {
  return put<TenantPolicy>(
    `/platform/tenancy/policies/${encodeURIComponent(policyId)}`,
    payload,
  )
}

export function listPermissionDenials(): Promise<AuditEventListResponse> {
  return get<AuditEventListResponse>("/audit/events", {
    params: {
      event_type: "authz.denied",
      limit: 50,
    },
  })
}
