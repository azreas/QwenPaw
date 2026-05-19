import type {
  BadCaseCategory,
  BadCaseCreateRequest,
  BadCaseItem,
  BadCaseStatus,
  BusinessTraceItem,
} from "@/api/types"

export interface BadCaseOption<T extends string> {
  label: string
  value: T
}

export interface BadCaseStatusTag {
  text: string
  color: "green" | "blue" | "orange" | "red" | "default"
}

export interface BadCaseStats {
  total: number
  open: number
  triaged: number
  transferred: number
  resolved: number
  ignored: number
}

export const BAD_CASE_CATEGORY_OPTIONS: BadCaseOption<BadCaseCategory>[] = [
  { label: "平台运行", value: "platform_runtime" },
  { label: "数据质量", value: "data_quality" },
  { label: "权限配置", value: "permission_config" },
  { label: "产品体验", value: "product_experience" },
]

export const BAD_CASE_STATUS_OPTIONS: BadCaseOption<BadCaseStatus>[] = [
  { label: "待处理", value: "open" },
  { label: "已分诊", value: "triaged" },
  { label: "已转交", value: "transferred" },
  { label: "已解决", value: "resolved" },
  { label: "已忽略", value: "ignored" },
]

const CATEGORY_LABELS = Object.fromEntries(
  BAD_CASE_CATEGORY_OPTIONS.map((item) => [item.value, item.label]),
) as Record<BadCaseCategory, string>

export function getBadCaseCategoryLabel(category: string): string {
  return CATEGORY_LABELS[category as BadCaseCategory] || category
}

export function getBadCaseStatusTag(status: string): BadCaseStatusTag {
  if (status === "open") return { text: "待处理", color: "red" }
  if (status === "triaged") return { text: "已分诊", color: "orange" }
  if (status === "transferred") return { text: "已转交", color: "blue" }
  if (status === "resolved") return { text: "已解决", color: "green" }
  if (status === "ignored") return { text: "已忽略", color: "default" }
  return { text: status || "未知", color: "default" }
}

export function buildBadCaseStats(items: BadCaseItem[]): BadCaseStats {
  return items.reduce<BadCaseStats>(
    (stats, item) => ({
      total: stats.total + 1,
      open: stats.open + (item.status === "open" ? 1 : 0),
      triaged: stats.triaged + (item.status === "triaged" ? 1 : 0),
      transferred: stats.transferred + (item.status === "transferred" ? 1 : 0),
      resolved: stats.resolved + (item.status === "resolved" ? 1 : 0),
      ignored: stats.ignored + (item.status === "ignored" ? 1 : 0),
    }),
    {
      total: 0,
      open: 0,
      triaged: 0,
      transferred: 0,
      resolved: 0,
      ignored: 0,
    },
  )
}

export function buildBadCaseCreateRequest(
  trace: BusinessTraceItem,
  values: {
    category: BadCaseCategory
    owner?: string
    note?: string
  },
): BadCaseCreateRequest {
  return {
    source_audit_id: trace.id,
    source_request_id: trace.request_id,
    source_trace_id: trace.trace_id,
    category: values.category,
    owner: values.owner?.trim() || "",
    note: values.note?.trim() || "",
  }
}
