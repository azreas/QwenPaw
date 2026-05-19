import { beforeEach, describe, expect, it, vi } from "vitest"
import { del, get, patch, post } from "./http"
import {
  addTenantEvalItems,
  convertBadCasesToEval,
  createTenantEvalDataset,
  createTenantEvalExecution,
  deleteTenantEvalDataset,
  exportTenantAcceptanceEvidence,
  getSampleEvalDataset,
  getTenantAccuracyReport,
  getTenantEvalExecution,
  getTenantEvalDataset,
  listTenantEvalDatasets,
  listTenantEvalExecutions,
  updateTenantEvalDataset,
} from "./evaluation"

vi.mock("./http", () => ({
  del: vi.fn(),
  get: vi.fn(),
  patch: vi.fn(),
  post: vi.fn(),
}))

describe("evaluation api", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("uses tenant path for dataset operations", async () => {
    vi.mocked(get).mockResolvedValue({ items: [], total: 0 })
    await listTenantEvalDatasets("wx_acme")
    expect(get).toHaveBeenCalledWith("/evaluation/tenants/wx_acme/datasets")

    vi.mocked(post).mockResolvedValue({ id: "dataset-1", items: [] })
    await createTenantEvalDataset("wx_acme", {
      name: "验收集",
      description: "一期验收",
      items: [],
    })
    expect(post).toHaveBeenCalledWith("/evaluation/tenants/wx_acme/datasets", {
      name: "验收集",
      description: "一期验收",
      items: [],
    })

    await createTenantEvalDataset("wx_acme", {
      name: "最小测评集",
    })
    expect(post).toHaveBeenLastCalledWith("/evaluation/tenants/wx_acme/datasets", {
      name: "最小测评集",
    })
  })

  it("encodes dataset and execution ids", async () => {
    vi.mocked(get).mockResolvedValue({ id: "dataset 1" })
    await getTenantEvalDataset("wx_acme", "dataset 1")
    expect(get).toHaveBeenCalledWith(
      "/evaluation/tenants/wx_acme/datasets/dataset%201",
    )

    vi.mocked(patch).mockResolvedValue({ id: "dataset 1" })
    await updateTenantEvalDataset("wx_acme", "dataset 1", { name: "新名称" })
    expect(patch).toHaveBeenCalledWith(
      "/evaluation/tenants/wx_acme/datasets/dataset%201",
      { name: "新名称" },
    )

    vi.mocked(del).mockResolvedValue(undefined)
    await deleteTenantEvalDataset("wx_acme", "dataset 1")
    expect(del).toHaveBeenCalledWith(
      "/evaluation/tenants/wx_acme/datasets/dataset%201",
    )

    vi.mocked(get).mockResolvedValue({ id: "exec 1" })
    await getTenantEvalExecution("wx_acme", "exec 1")
    expect(get).toHaveBeenLastCalledWith(
      "/evaluation/tenants/wx_acme/executions/exec%201",
    )
  })

  it("rejects empty dataset id before requesting", async () => {
    await expect(getTenantEvalDataset("wx_acme", "")).rejects.toThrow(
      "datasetId is required",
    )
    expect(get).not.toHaveBeenCalled()
  })

  it("rejects empty execution id before requesting report", async () => {
    await expect(getTenantAccuracyReport("wx_acme", "")).rejects.toThrow(
      "executionId is required",
    )
    expect(get).not.toHaveBeenCalled()
  })

  it("gets tenant acceptance evidence with encoded execution id", async () => {
    vi.mocked(get).mockResolvedValue({ evidence_version: "1" })

    await exportTenantAcceptanceEvidence("wx_acme", "exec 1")

    expect(get).toHaveBeenCalledWith(
      "/evaluation/tenants/wx_acme/executions/exec%201/evidence",
    )
  })

  it("adds items and creates executions", async () => {
    const item = {
      case_id: "case-1",
      category: "indicator_query" as const,
      question: "营收是多少？",
      expected: "返回营收",
      entrypoint: "both" as const,
      ability: "indicator_query",
      owner: "data_quality",
      tags: [],
    }

    vi.mocked(post).mockResolvedValue({ id: "dataset-1", items: [item] })
    await addTenantEvalItems("wx_acme", "dataset-1", { items: [item] })
    expect(post).toHaveBeenCalledWith(
      "/evaluation/tenants/wx_acme/datasets/dataset-1/items",
      { items: [item] },
    )

    await addTenantEvalItems("wx_acme", "dataset-1", {
      items: [
        {
          category: "indicator_query",
          question: "本月营收是多少？",
          expected: "返回营收值",
        },
      ],
    })
    expect(post).toHaveBeenLastCalledWith(
      "/evaluation/tenants/wx_acme/datasets/dataset-1/items",
      {
        items: [
          {
            category: "indicator_query",
            question: "本月营收是多少？",
            expected: "返回营收值",
          },
        ],
      },
    )

    await createTenantEvalExecution("wx_acme", {
      dataset_id: "dataset-1",
      items: [{ case_id: "case-1", result: "correct", actual: "100万" }],
    })
    expect(post).toHaveBeenCalledWith("/evaluation/tenants/wx_acme/executions", {
      dataset_id: "dataset-1",
      items: [{ case_id: "case-1", result: "correct", actual: "100万" }],
    })
  })

  it("lists executions with dataset filter and gets report", async () => {
    vi.mocked(get).mockResolvedValue({ items: [], total: 0 })
    await listTenantEvalExecutions("wx_acme", { dataset_id: "dataset-1" })
    expect(get).toHaveBeenCalledWith("/evaluation/tenants/wx_acme/executions", {
      params: { dataset_id: "dataset-1" },
    })

    await getTenantAccuracyReport("wx_acme", "exec 1")
    expect(get).toHaveBeenCalledWith(
      "/evaluation/tenants/wx_acme/executions/exec%201/report",
    )
  })

  it("uses global sample and tenant bad-case conversion path", async () => {
    vi.mocked(get).mockResolvedValue({ name: "样例测评集", items: [] })
    await getSampleEvalDataset()
    expect(get).toHaveBeenCalledWith("/evaluation/datasets/sample")

    vi.mocked(post).mockResolvedValue({ dataset_id: "dataset-1", converted: 2 })
    await convertBadCasesToEval("wx_acme", {
      case_ids: ["case-1", "case-2"],
      dataset_id: "dataset-1",
      dataset_name: "",
    })
    expect(post).toHaveBeenCalledWith(
      "/evaluation/tenants/wx_acme/bad-case-to-eval",
      {
        case_ids: ["case-1", "case-2"],
        dataset_id: "dataset-1",
        dataset_name: "",
      },
    )
  })
})
