import type { BusinessCallItem, BusinessCallQuery } from "@/api/audit"
import type { TenantOpsSummaryResponse } from "@/api/types"

export interface StatusTag {
  text: string
  color: "green" | "blue" | "orange" | "red" | "default"
}

export interface TraceStats {
  businessCalls24h: number
  failedCalls24h: number
  visibleTotal: number
  visibleFailures: number
}

export const TRACE_CALL_TYPE_OPTIONS = [
  { label: "Agent", value: "agent" },
  { label: "Skill", value: "skill" },
  { label: "MCP", value: "mcp" },
  { label: "Builtin Tool", value: "builtin_tool" },
  { label: "Runtime Extension", value: "runtime_extension" },
  { label: "Authz", value: "authz" },
  { label: "Tenant Boundary", value: "tenant_boundary" },
  { label: "Quota", value: "quota" },
  { label: "Policy", value: "policy" },
  { label: "Tool Guard", value: "tool_guard" },
]

export const TRACE_STATUS_OPTIONS = [
  { label: "成功", value: "success" },
  { label: "失败", value: "failure" },
  { label: "拒绝", value: "denied" },
  { label: "跳过", value: "skipped" },
  { label: "超时", value: "timeout" },
  { label: "取消", value: "cancelled" },
  { label: "降级", value: "degraded" },
]

export function getHealthStatusTag(status: string): StatusTag {
  if (status === "healthy") {
    return { text: "健康", color: "green" }
  }
  if (status === "stopped") {
    return { text: "已停止", color: "default" }
  }
  if (status === "unknown") {
    return { text: "未知", color: "orange" }
  }
  return { text: status || "未知", color: "default" }
}

export function getTraceStatusTag(status: string): StatusTag {
  if (status === "success") {
    return { text: "成功", color: "green" }
  }
  if (status === "failure") {
    return { text: "失败", color: "red" }
  }
  if (status === "denied") {
    return { text: "拒绝", color: "orange" }
  }
  if (status === "skipped") {
    return { text: "跳过", color: "default" }
  }
  if (status === "timeout") {
    return { text: "超时", color: "red" }
  }
  if (status === "cancelled") {
    return { text: "取消", color: "default" }
  }
  if (status === "degraded") {
    return { text: "降级", color: "orange" }
  }
  return { text: status || "未知", color: "default" }
}

export function isTraceSuccessful(status: string): boolean {
  return status === "success"
}

function titleCaseTraceValue(value: string): string {
  return value
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ")
}

export function formatTraceCallType(
  trace: Pick<BusinessCallItem, "call_type" | "ability_type">,
): string {
  const value = trace.call_type || trace.ability_type || ""
  if (!value) {
    return "-"
  }
  if (value === "mcp") {
    return "MCP"
  }
  return titleCaseTraceValue(value)
}

export function formatTraceCallName(
  trace: Pick<BusinessCallItem, "call_name" | "ability_name">,
): string {
  return trace.call_name || trace.ability_name || "-"
}

export function summarizeTraceStats(
  summary: TenantOpsSummaryResponse | null,
  traces: BusinessCallItem[],
): TraceStats {
  return {
    businessCalls24h: summary?.business_calls_24h ?? 0,
    failedCalls24h: summary?.failed_calls_24h ?? 0,
    visibleTotal: traces.length,
    visibleFailures: traces.filter((item) => !isTraceSuccessful(item.status)).length,
  }
}

export function formatFailureRate(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}

export function buildTraceFilters(
  values: Partial<BusinessCallQuery>,
): BusinessCallQuery {
  const query: BusinessCallQuery = {
    limit: values.limit ?? 100,
  }

  if (values.call_type) {
    query.call_type = values.call_type
  }

  const callName = values.call_name?.trim()
  if (callName) {
    query.call_name = callName
  }

  if (values.ability_type) {
    query.ability_type = values.ability_type
  }

  const abilityName = values.ability_name?.trim()
  if (abilityName) {
    query.ability_name = abilityName
  }

  const entrypoint = values.entrypoint?.trim()
  if (entrypoint) {
    query.entrypoint = entrypoint
  }

  const status = values.status?.trim()
  if (status) {
    query.status = status
  }

  const errorReason = values.error_reason?.trim()
  if (errorReason) {
    query.error_reason = errorReason
  }

  const errorCode = values.error_code?.trim()
  if (errorCode) {
    query.error_code = errorCode
  }

  const requestId = values.request_id?.trim()
  if (requestId) {
    query.request_id = requestId
  }

  const traceId = values.trace_id?.trim()
  if (traceId) {
    query.trace_id = traceId
  }

  return query
}
