import { describe, expect, it } from "vitest"
import {
  BAD_CASE_CATEGORY_OPTIONS,
  BAD_CASE_STATUS_OPTIONS,
  buildBadCaseCreateRequest,
  buildBadCaseStats,
  getBadCaseCategoryLabel,
  getBadCaseStatusTag,
} from "./badCaseModel"
import type { BadCaseItem, BusinessTraceItem } from "@/api/types"

const cases: BadCaseItem[] = [
  {
    case_id: "case-audit-1",
    source_audit_id: "audit-1",
    source_request_id: "req-1",
    source_trace_id: "trace-1",
    category: "data_quality",
    status: "open",
    owner: "data-team",
    note: "wrong answer",
    ability_type: "skill",
    ability_name: "sales_report",
    entrypoint: "webchat",
    created_at: "2026-05-13T08:00:00+00:00",
    updated_at: "2026-05-13T08:00:00+00:00",
  },
  {
    case_id: "case-audit-2",
    source_audit_id: "audit-2",
    source_request_id: "req-2",
    source_trace_id: "trace-2",
    category: "platform_runtime",
    status: "resolved",
    owner: "ops-team",
    note: "fixed",
    ability_type: "mcp",
    ability_name: "erp",
    entrypoint: "wecom",
    created_at: "2026-05-13T08:10:00+00:00",
    updated_at: "2026-05-13T09:00:00+00:00",
  },
]

const trace: BusinessTraceItem = {
  id: "audit-3",
  tenant_id: "acme",
  agent_id: "wx_acme",
  session_id: "session-1",
  actor_id: "user-1",
  entrypoint: "webchat",
  ability_type: "skill",
  ability_name: "finance_query",
  duration_ms: 800,
  status: "failure",
  error_reason: "permission denied",
  request_id: "req-3",
  trace_id: "trace-3",
  created_at: "2026-05-13T09:30:00+00:00",
}

describe("badCaseModel", () => {
  it("exposes category and status options", () => {
    expect(BAD_CASE_CATEGORY_OPTIONS.map((item) => item.value)).toEqual([
      "platform_runtime",
      "data_quality",
      "permission_config",
      "product_experience",
    ])
    expect(BAD_CASE_STATUS_OPTIONS.map((item) => item.value)).toEqual([
      "open",
      "triaged",
      "transferred",
      "resolved",
      "ignored",
    ])
  })

  it("builds bad case stats", () => {
    expect(buildBadCaseStats(cases)).toEqual({
      total: 2,
      open: 1,
      triaged: 0,
      transferred: 0,
      resolved: 1,
      ignored: 0,
    })
  })

  it("maps labels and status tags", () => {
    expect(getBadCaseCategoryLabel("data_quality")).toBe("数据质量")
    expect(getBadCaseCategoryLabel("custom")).toBe("custom")
    expect(getBadCaseStatusTag("open")).toEqual({ text: "待处理", color: "red" })
    expect(getBadCaseStatusTag("resolved")).toEqual({
      text: "已解决",
      color: "green",
    })
  })

  it("builds create request from business trace", () => {
    expect(
      buildBadCaseCreateRequest(trace, {
        category: "permission_config",
        owner: "ops",
        note: "needs permission review",
      }),
    ).toEqual({
      source_audit_id: "audit-3",
      source_request_id: "req-3",
      source_trace_id: "trace-3",
      category: "permission_config",
      owner: "ops",
      note: "needs permission review",
    })
  })
})
