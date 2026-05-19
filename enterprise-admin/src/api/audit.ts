import { get } from "./http"
import type { AuditEventListResponse } from "./types"

export type BusinessCallType =
  | "agent"
  | "skill"
  | "mcp"
  | "builtin_tool"
  | "runtime_extension"
  | "authz"
  | "tenant_boundary"
  | "quota"
  | "policy"
  | "tool_guard"
  | string

export type BusinessCallStatus =
  | "success"
  | "failure"
  | "denied"
  | "skipped"
  | "timeout"
  | "cancelled"
  | "degraded"
  | string

export interface AuditEventQuery {
  tenant_id?: string
  event_type?: string
  outcome?: string
  resource_type?: string
  limit?: number
}

export interface BusinessCallItem {
  id: string
  tenant_id: string
  agent_id: string
  session_id?: string | null
  actor_id?: string | null
  entrypoint?: string | null
  call_type?: BusinessCallType | null
  call_name?: string | null
  ability_type?: string | null
  ability_name?: string | null
  duration_ms?: number | null
  status: BusinessCallStatus
  error_code?: string | null
  error_reason?: string | null
  request_id?: string | null
  trace_id?: string | null
  created_at: string
}

export interface BusinessCallListResponse {
  items: BusinessCallItem[]
  total: number
}

export interface BusinessCallQuery {
  tenant_id?: string
  agent_id?: string
  call_type?: BusinessCallType
  call_name?: string
  ability_type?: string
  ability_name?: string
  entrypoint?: string
  status?: BusinessCallStatus
  error_code?: string
  error_reason?: string
  request_id?: string
  trace_id?: string
  limit?: number
}

export function listAuditEvents(
  query: AuditEventQuery = {},
): Promise<AuditEventListResponse> {
  return get<AuditEventListResponse>("/audit/events", { params: query })
}

export function listBusinessCalls(
  query: BusinessCallQuery = {},
): Promise<BusinessCallListResponse> {
  return get<BusinessCallListResponse>("/audit/business-calls", {
    params: query,
  })
}
