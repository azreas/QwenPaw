import { describe, expect, it } from "vitest"
import {
  buildTraceFilters,
  formatTraceCallName,
  formatTraceCallType,
  formatFailureRate,
  getHealthStatusTag,
  getTraceStatusTag,
  isTraceSuccessful,
  summarizeTraceStats,
  TRACE_CALL_TYPE_OPTIONS,
} from "./traceModel"
import type { BusinessCallItem } from "@/api/audit"
import type { TenantOpsSummaryResponse } from "@/api/types"

const summary: TenantOpsSummaryResponse = {
  tenant_id: "acme",
  agent_id: "wx_acme",
  health_status: "healthy",
  last_activity_at: "2026-05-13T08:30:00+00:00",
  business_calls_24h: 10,
  failed_calls_24h: 2,
  recent_failures: [],
}

const traces: BusinessCallItem[] = [
  {
    id: "trace-1",
    tenant_id: "acme",
    agent_id: "wx_acme",
    session_id: "session-1",
    actor_id: "user-1",
    entrypoint: "webchat",
    ability_type: "skill",
    ability_name: "sales_report",
    call_type: "skill",
    call_name: "sales_report",
    duration_ms: 45,
    status: "success",
    error_code: "",
    error_reason: "",
    request_id: "req-1",
    trace_id: "trace-1",
    created_at: "2026-05-13T08:00:00+00:00",
  },
  {
    id: "trace-2",
    tenant_id: "acme",
    agent_id: "wx_acme",
    session_id: "session-2",
    actor_id: "user-2",
    entrypoint: "wecom",
    ability_type: "mcp",
    ability_name: "erp_query",
    call_type: "mcp",
    call_name: "erp_query",
    duration_ms: 1200,
    status: "timeout",
    error_code: "mcp.timeout",
    error_reason: "timeout",
    request_id: "req-2",
    trace_id: "trace-2",
    created_at: "2026-05-13T08:10:00+00:00",
  },
]

describe("traceModel", () => {
  it("summarizes trace stats", () => {
    expect(summarizeTraceStats(summary, traces)).toEqual({
      businessCalls24h: 10,
      failedCalls24h: 2,
      visibleTotal: 2,
      visibleFailures: 1,
    })
  })

  it("maps health and trace status tags", () => {
    expect(getHealthStatusTag("healthy")).toEqual({ text: "健康", color: "green" })
    expect(getHealthStatusTag("stopped")).toEqual({ text: "已停止", color: "default" })
    expect(getTraceStatusTag("success")).toEqual({ text: "成功", color: "green" })
    expect(getTraceStatusTag("failure")).toEqual({ text: "失败", color: "red" })
    expect(getTraceStatusTag("denied")).toEqual({ text: "拒绝", color: "orange" })
    expect(getTraceStatusTag("timeout")).toEqual({ text: "超时", color: "red" })
    expect(getTraceStatusTag("cancelled")).toEqual({ text: "取消", color: "default" })
    expect(getTraceStatusTag("degraded")).toEqual({ text: "降级", color: "orange" })
  })

  it("treats only success as successful", () => {
    expect(isTraceSuccessful("success")).toBe(true)
    for (const status of ["failure", "denied", "timeout", "cancelled", "degraded"]) {
      expect(isTraceSuccessful(status)).toBe(false)
    }
  })

  it("exposes every P0 call type as a display option", () => {
    expect(TRACE_CALL_TYPE_OPTIONS.map((item) => item.value)).toEqual([
      "agent",
      "skill",
      "mcp",
      "builtin_tool",
      "runtime_extension",
      "authz",
      "tenant_boundary",
      "quota",
      "policy",
      "tool_guard",
    ])
  })

  it("formats new call fields and falls back to legacy ability fields", () => {
    expect(formatTraceCallType({ call_type: "runtime_extension" })).toBe(
      "Runtime Extension",
    )
    expect(formatTraceCallType({ ability_type: "skill" })).toBe("Skill")
    expect(formatTraceCallName({ call_name: "quota.daily" })).toBe("quota.daily")
    expect(formatTraceCallName({ ability_name: "sales_report" })).toBe(
      "sales_report",
    )
    expect(formatTraceCallName({})).toBe("-")
  })

  it("formats failure rate", () => {
    expect(formatFailureRate(0.125)).toBe("12.5%")
  })

  it("normalizes trace filters", () => {
    expect(
      buildTraceFilters({
        call_type: "skill",
        call_name: "  sales_report  ",
        error_code: " policy.denied ",
        request_id: " req-1 ",
        trace_id: " trace-1 ",
        entrypoint: "",
        status: " denied ",
        error_reason: " timeout ",
      }),
    ).toEqual({
      call_type: "skill",
      call_name: "sales_report",
      status: "denied",
      error_code: "policy.denied",
      error_reason: "timeout",
      request_id: "req-1",
      trace_id: "trace-1",
      limit: 100,
    })
  })

  it("keeps explicit limit and drops blank strings", () => {
    expect(
      buildTraceFilters({
        call_name: "   ",
        ability_name: " legacy ",
        entrypoint: " webchat ",
        status: "",
        error_code: " ",
        error_reason: " ",
        limit: 20,
      }),
    ).toEqual({
      ability_name: "legacy",
      entrypoint: "webchat",
      limit: 20,
    })
  })
})
