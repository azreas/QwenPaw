import { describe, expect, it } from "vitest"
import type { EvalDataset } from "@/api/types"
import {
  EVAL_ACTION_OPTIONS,
  EVAL_CATEGORY_OPTIONS,
  EVAL_ENTRYPOINT_OPTIONS,
  EVAL_ISSUE_OWNER_OPTIONS,
  EVAL_RESULT_OPTIONS,
  buildDatasetStats,
  buildExecutionPayload,
  buildExecutionStats,
  formatAccuracyRate,
  getEvalCategoryLabel,
  getEvalResultTag,
  getIssueOwnerLabel,
} from "./evaluationModel"

const dataset: EvalDataset = {
  id: "dataset-1",
  tenant_id: "acme",
  name: "验收集",
  description: "一期验收",
  created_at: "2026-05-13T08:00:00+00:00",
  updated_at: "2026-05-13T08:00:00+00:00",
  items: [
    {
      case_id: "case-1",
      category: "indicator_query",
      question: "营收是多少？",
      expected: "返回营收",
      entrypoint: "both",
      ability: "indicator_query",
      owner: "data_quality",
      tags: ["finance"],
    },
    {
      case_id: "case-2",
      category: "permission_boundary",
      question: "能看别人薪资吗？",
      expected: "拒绝访问",
      entrypoint: "webchat",
      ability: "indicator_query",
      owner: "permission_config",
      tags: [],
    },
  ],
}

describe("evaluationModel", () => {
  it("provides stable option lists", () => {
    expect(EVAL_CATEGORY_OPTIONS.map((item) => item.value)).toEqual([
      "indicator_query",
      "jargon_explain",
      "knowledge_retrieval",
      "permission_boundary",
      "product_experience",
    ])
    expect(EVAL_ENTRYPOINT_OPTIONS.map((item) => item.value)).toEqual([
      "webchat",
      "wecom_bot",
      "both",
    ])
    expect(EVAL_RESULT_OPTIONS).toContainEqual({
      label: "部分正确",
      value: "partial",
    })
    expect(EVAL_ISSUE_OWNER_OPTIONS).toContainEqual({
      label: "数据质量",
      value: "data_quality",
    })
    expect(EVAL_ACTION_OPTIONS).toContainEqual({
      label: "关闭",
      value: "close",
    })
  })

  it("maps labels and result tags", () => {
    expect(getEvalCategoryLabel("indicator_query")).toBe("指标查询")
    expect(getIssueOwnerLabel("data_quality")).toBe("数据质量")
    expect(getIssueOwnerLabel("")).toBe("-")
    expect(getIssueOwnerLabel(undefined)).toBe("-")
    expect(getEvalCategoryLabel("custom")).toBe("custom")
    expect(getEvalResultTag("correct")).toEqual({ text: "正确", color: "green" })
    expect(getEvalResultTag("partial")).toEqual({
      text: "部分正确",
      color: "orange",
    })
    expect(getEvalResultTag("blocked")).toEqual({ text: "阻塞", color: "default" })
  })

  it("builds dataset stats", () => {
    expect(buildDatasetStats([dataset])).toEqual({
      totalDatasets: 1,
      totalItems: 2,
      permissionBoundaryItems: 1,
      fromBadCaseItems: 0,
    })
  })

  it("builds execution stats and formats rates", () => {
    const stats = buildExecutionStats([
      {
        id: "exec-1",
        tenant_id: "acme",
        dataset_id: "dataset-1",
        created_at: "2026-05-13T09:00:00+00:00",
        items: [
          { case_id: "case-1", result: "correct" },
          { case_id: "case-2", result: "partial" },
          { case_id: "case-3", result: "wrong", issue_owner: "permission_config" },
        ],
      },
    ])
    expect(stats).toEqual({
      totalExecutions: 1,
      totalExecutedItems: 3,
      correctItems: 1,
      partialItems: 1,
      wrongItems: 1,
      blockedItems: 0,
    })
    expect(formatAccuracyRate(0.875)).toBe("87.5%")
    expect(formatAccuracyRate(0.5)).toBe("50.0%")
    expect(formatAccuracyRate(undefined)).toBe("-")
    expect(formatAccuracyRate(null as unknown as number)).toBe("-")
    expect(formatAccuracyRate(Number.NaN)).toBe("-")
  })

  it("builds manual execution payload", () => {
    const payload = buildExecutionPayload(dataset, {
      "case-1": {
        actual: "  营收 100 万  ",
        result: "correct",
        issue_owner: null,
        action: "close",
        note: "  符合预期  ",
        trace_id: " trace-1 ",
        request_id: " req-1 ",
      },
    })

    expect(payload).toEqual({
      dataset_id: "dataset-1",
      items: [
        {
          case_id: "case-1",
          actual: "营收 100 万",
          result: "correct",
          issue_owner: null,
          action: "close",
          note: "符合预期",
          trace_id: "trace-1",
          request_id: "req-1",
        },
        {
          case_id: "case-2",
          actual: "",
          result: "blocked",
          issue_owner: null,
          action: null,
          note: "",
          trace_id: "",
          request_id: "",
        },
      ],
    })
  })
})
