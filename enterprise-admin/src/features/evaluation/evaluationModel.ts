import type {
  CreateEvalExecutionRequest,
  EvalAction,
  EvalCategory,
  EvalDataset,
  EvalEntrypoint,
  EvalExecution,
  EvalExecutionItem,
  EvalResult,
  IssueOwner,
} from "@/api/types"

export interface EvalOption<T extends string> {
  label: string
  value: T
}

export interface EvalResultTag {
  text: string
  color: "green" | "blue" | "orange" | "red" | "default"
}

export interface DatasetStats {
  totalDatasets: number
  totalItems: number
  permissionBoundaryItems: number
  fromBadCaseItems: number
}

export interface ExecutionStats {
  totalExecutions: number
  totalExecutedItems: number
  correctItems: number
  partialItems: number
  wrongItems: number
  blockedItems: number
}

export type ManualExecutionItem = Omit<
  EvalExecutionItem,
  "case_id" | "executed_at"
>

export type ManualExecutionValues = Partial<Record<string, ManualExecutionItem>>

export const EVAL_CATEGORY_OPTIONS: EvalOption<EvalCategory>[] = [
  { label: "指标查询", value: "indicator_query" },
  { label: "术语解释", value: "jargon_explain" },
  { label: "知识检索", value: "knowledge_retrieval" },
  { label: "权限边界", value: "permission_boundary" },
  { label: "产品体验", value: "product_experience" },
]

export const EVAL_ENTRYPOINT_OPTIONS: EvalOption<EvalEntrypoint>[] = [
  { label: "WebChat", value: "webchat" },
  { label: "企微 Bot", value: "wecom_bot" },
  { label: "双入口", value: "both" },
]

export const EVAL_RESULT_OPTIONS: EvalOption<EvalResult>[] = [
  { label: "正确", value: "correct" },
  { label: "部分正确", value: "partial" },
  { label: "错误", value: "wrong" },
  { label: "阻塞", value: "blocked" },
]

export const EVAL_ISSUE_OWNER_OPTIONS: EvalOption<IssueOwner>[] = [
  { label: "数据质量", value: "data_quality" },
  { label: "平台运行", value: "platform_runtime" },
  { label: "权限配置", value: "permission_config" },
  { label: "产品体验", value: "product_experience" },
]

export const EVAL_ACTION_OPTIONS: EvalOption<EvalAction>[] = [
  { label: "修复", value: "fix" },
  { label: "转交", value: "transfer" },
  { label: "进入 Backlog", value: "backlog" },
  { label: "关闭", value: "close" },
]

const CATEGORY_LABELS = Object.fromEntries(
  EVAL_CATEGORY_OPTIONS.map((item) => [item.value, item.label]),
) as Record<EvalCategory, string>

const ISSUE_OWNER_LABELS = Object.fromEntries(
  EVAL_ISSUE_OWNER_OPTIONS.map((item) => [item.value, item.label]),
) as Record<IssueOwner, string>

const RESULT_TAGS: Record<EvalResult, EvalResultTag> = {
  correct: { text: "正确", color: "green" },
  partial: { text: "部分正确", color: "orange" },
  wrong: { text: "错误", color: "red" },
  blocked: { text: "阻塞", color: "default" },
}

function normalizeText(value?: string): string {
  return value?.trim() || ""
}

export function getEvalCategoryLabel(category: string): string {
  return CATEGORY_LABELS[category as EvalCategory] || category
}

export function getIssueOwnerLabel(owner?: string | null): string {
  if (!owner) return "-"
  return ISSUE_OWNER_LABELS[owner as IssueOwner] || owner
}

export function getEvalResultTag(result: string): EvalResultTag {
  return RESULT_TAGS[result as EvalResult] || {
    text: result || "未知",
    color: "default",
  }
}

export function formatAccuracyRate(rate?: number | null): string {
  if (rate == null || Number.isNaN(rate)) {
    return "-"
  }
  return `${(rate * 100).toFixed(1)}%`
}

export function buildDatasetStats(datasets: EvalDataset[]): DatasetStats {
  return datasets.reduce<DatasetStats>(
    (stats, dataset) => {
      const items = dataset.items || []
      return {
        totalDatasets: stats.totalDatasets + 1,
        totalItems: stats.totalItems + items.length,
        permissionBoundaryItems:
          stats.permissionBoundaryItems +
          items.filter((item) => item.category === "permission_boundary").length,
        fromBadCaseItems:
          stats.fromBadCaseItems +
          items.filter((item) => (item.tags ?? []).includes("from_bad_case"))
            .length,
      }
    },
    {
      totalDatasets: 0,
      totalItems: 0,
      permissionBoundaryItems: 0,
      fromBadCaseItems: 0,
    },
  )
}

export function buildExecutionStats(executions: EvalExecution[]): ExecutionStats {
  return executions.reduce<ExecutionStats>(
    (stats, execution) => {
      const items = execution.items || []
      return {
        totalExecutions: stats.totalExecutions + 1,
        totalExecutedItems: stats.totalExecutedItems + items.length,
        correctItems:
          stats.correctItems +
          items.filter((item) => item.result === "correct").length,
        partialItems:
          stats.partialItems +
          items.filter((item) => item.result === "partial").length,
        wrongItems:
          stats.wrongItems + items.filter((item) => item.result === "wrong").length,
        blockedItems:
          stats.blockedItems +
          items.filter((item) => item.result === "blocked").length,
      }
    },
    {
      totalExecutions: 0,
      totalExecutedItems: 0,
      correctItems: 0,
      partialItems: 0,
      wrongItems: 0,
      blockedItems: 0,
    },
  )
}

export function buildExecutionPayload(
  dataset: EvalDataset,
  values: ManualExecutionValues,
): CreateEvalExecutionRequest {
  return {
    dataset_id: dataset.id,
    items: dataset.items.map((item) => {
      const executionItem = values[item.case_id]
      return {
        case_id: item.case_id,
        actual: normalizeText(executionItem?.actual),
        result: executionItem?.result || "blocked",
        issue_owner: executionItem?.issue_owner ?? null,
        action: executionItem?.action ?? null,
        note: normalizeText(executionItem?.note),
        trace_id: normalizeText(executionItem?.trace_id),
        request_id: normalizeText(executionItem?.request_id),
      }
    }),
  }
}
