import { act, render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { Form, message } from "antd"
import { beforeEach, describe, expect, it, vi } from "vitest"
import EvaluationPage from "./EvaluationPage"
import { listTenantBadCases } from "@/api/ops"
import {
  convertBadCasesToEval,
  createTenantEvalDataset,
  createTenantEvalExecution,
  exportTenantAcceptanceEvidence,
  getSampleEvalDataset,
  getTenantAccuracyReport,
  listTenantEvalDatasets,
  listTenantEvalExecutions,
} from "@/api/evaluation"
import { listWecomTenants } from "@/api/tenants"
import type {
  AcceptanceEvidenceExport,
  AccuracyReport,
  EvalDataset,
  EvalExecution,
  WecomTenantSummary,
} from "@/api/types"

const messageErrorSpy = vi.spyOn(message, "error").mockImplementation(() => {
  const close = () => undefined
  return close as never
})

const messageSuccessSpy = vi.spyOn(message, "success").mockImplementation(() => {
  const close = () => undefined
  return close as never
})

vi.mock("@/api/tenants", () => ({
  listWecomTenants: vi.fn(),
}))

vi.mock("@/api/ops", () => ({
  listTenantBadCases: vi.fn(),
}))

vi.mock("@/api/evaluation", () => ({
  convertBadCasesToEval: vi.fn(),
  createTenantEvalDataset: vi.fn(),
  createTenantEvalExecution: vi.fn(),
  exportTenantAcceptanceEvidence: vi.fn(),
  getSampleEvalDataset: vi.fn(),
  getTenantAccuracyReport: vi.fn(),
  listTenantEvalDatasets: vi.fn(),
  listTenantEvalExecutions: vi.fn(),
}))

const tenant = {
  tenant_id: "acme",
  agent_id: "wx_acme",
  workspace_dir: "D:/tenants/wx_acme",
  exists: true,
  initialized: true,
  running: true,
  updated_at: "2026-05-13T08:00:00+00:00",
  chat_count: 3,
  job_count: 1,
  source: "workspace",
}

const secondTenant: WecomTenantSummary = {
  tenant_id: "beta",
  agent_id: "wx_beta",
  workspace_dir: "D:/tenants/wx_beta",
  exists: true,
  initialized: true,
  running: true,
  updated_at: "2026-05-13T09:00:00+00:00",
  chat_count: 4,
  job_count: 2,
  source: "workspace",
}

const dataset: EvalDataset = {
  id: "dataset-1",
  tenant_id: "acme",
  name: "一期验收集",
  description: "覆盖核心指标和权限边界",
  created_at: "2026-05-13T08:00:00+00:00",
  updated_at: "2026-05-13T08:00:00+00:00",
  items: [
    {
      case_id: "case-1",
      category: "indicator_query",
      question: "上月营收是多少？",
      expected: "返回上月营收",
      entrypoint: "both",
      ability: "indicator_query",
      owner: "data_quality",
      tags: [],
    },
    {
      case_id: "case-2",
      category: "permission_boundary",
      question: "能查看其他部门薪资吗？",
      expected: "拒绝访问",
      entrypoint: "webchat",
      ability: "indicator_query",
      owner: "permission_config",
      tags: ["from_bad_case"],
    },
  ],
}

const execution: EvalExecution = {
  id: "exec-1",
  tenant_id: "acme",
  dataset_id: "dataset-1",
  created_at: "2026-05-13T09:00:00+00:00",
  items: [{ case_id: "case-1", result: "correct", actual: "100万" }],
}

const evidence: AcceptanceEvidenceExport = {
  tenant_id: "acme",
  agent_id: "wx_acme",
  dataset,
  execution,
  report: {
    dataset_id: "dataset-1",
    execution_id: "exec-1",
    total: 1,
    executable: 1,
    correct: 1,
    partial: 0,
    wrong: 0,
    blocked: 0,
    correct_rate: 1,
    partial_rate: 0,
    issue_distribution: {},
    created_at: "2026-05-13T09:00:00+00:00",
  },
  exported_at: "2026-05-13T10:00:00+00:00",
  evidence_version: "1",
}

const secondExecution: EvalExecution = {
  id: "exec-2",
  tenant_id: "acme",
  dataset_id: "dataset-1",
  created_at: "2026-05-13T10:00:00+00:00",
  items: [{ case_id: "case-2", result: "wrong", actual: "无权限" }],
}

const secondDataset: EvalDataset = {
  id: "dataset-2",
  tenant_id: "beta",
  name: "二期验收集",
  description: "覆盖 beta 租户核心链路",
  created_at: "2026-05-13T10:00:00+00:00",
  updated_at: "2026-05-13T10:00:00+00:00",
  items: [
    {
      case_id: "case-3",
      category: "knowledge_retrieval",
      question: "beta 租户知识库入口在哪？",
      expected: "返回 beta 知识库入口",
      entrypoint: "wecom_bot",
      ability: "knowledge_retrieval",
      owner: "platform_runtime",
      tags: [],
    },
  ],
}

const badCases = [
  {
    case_id: "case-bad-1",
    source_audit_id: "audit-1",
    source_request_id: "request-1",
    source_trace_id: "trace-1",
    category: "data_quality",
    status: "open",
    owner: "alice",
    note: "指标口径不一致",
    ability_type: "skill",
    ability_name: "indicator_query",
    entrypoint: "webchat",
    created_at: "2026-05-13T11:00:00+00:00",
    updated_at: "2026-05-13T11:00:00+00:00",
  },
  {
    case_id: "case-bad-2",
    source_audit_id: "audit-2",
    source_request_id: "request-2",
    source_trace_id: "trace-2",
    category: "permission_config",
    status: "triaged",
    owner: "bob",
    note: "权限放大",
    ability_type: "mcp",
    ability_name: "permission_guard",
    entrypoint: "wecom_bot",
    created_at: "2026-05-13T12:00:00+00:00",
    updated_at: "2026-05-13T12:00:00+00:00",
  },
]

function createDeferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

describe("EvaluationPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    messageErrorSpy.mockClear()
    messageSuccessSpy.mockClear()
    vi.mocked(listWecomTenants).mockResolvedValue({ tenants: [tenant] })
    vi.mocked(listTenantBadCases).mockResolvedValue({ items: [], total: 0 })
    vi.mocked(listTenantEvalDatasets).mockResolvedValue({
      items: [dataset],
      total: 1,
    })
    vi.mocked(listTenantEvalExecutions).mockResolvedValue({
      items: [execution],
      total: 1,
    })
    vi.mocked(convertBadCasesToEval).mockResolvedValue({
      dataset_id: "dataset-1",
      converted: 0,
      skipped: 0,
      items: [],
    })
    vi.mocked(createTenantEvalDataset).mockResolvedValue(dataset)
    vi.mocked(createTenantEvalExecution).mockResolvedValue(execution)
    vi.mocked(exportTenantAcceptanceEvidence).mockResolvedValue(evidence)
    vi.mocked(getSampleEvalDataset).mockResolvedValue(dataset)
    vi.mocked(getTenantAccuracyReport).mockResolvedValue({
      dataset_id: "dataset-1",
      execution_id: "exec-1",
      total: 1,
      executable: 1,
      correct: 1,
      partial: 0,
      wrong: 0,
      blocked: 0,
      correct_rate: 1,
      partial_rate: 0,
      issue_distribution: {},
      created_at: "2026-05-13T09:00:00+00:00",
    })
  })

  it("loads default tenant and renders dataset stats", async () => {
    render(<EvaluationPage />)

    expect(
      await screen.findByRole("heading", { name: "验收测评" }),
    ).toBeInTheDocument()
    expect(await screen.findByText("acme / wx_acme")).toBeInTheDocument()
    expect(screen.getAllByText("测评集").length).toBeGreaterThan(0)
    expect(screen.getAllByText("题目数").length).toBeGreaterThan(0)
    expect(screen.getByText("权限边界题")).toBeInTheDocument()
    expect(screen.getByText("Bad Case 转入")).toBeInTheDocument()
    expect(await screen.findByText("一期验收集")).toBeInTheDocument()

    expect(listTenantEvalDatasets).toHaveBeenCalledWith("wx_acme")
    expect(listTenantEvalExecutions).toHaveBeenCalledWith("wx_acme", {})
  })

  it("creates dataset from sample", async () => {
    render(<EvaluationPage />)

    await userEvent.click(await screen.findByRole("button", { name: "从样例创建" }))

    await waitFor(() => {
      expect(createTenantEvalDataset).toHaveBeenCalledWith("wx_acme", {
        name: dataset.name,
        description: dataset.description,
        items: dataset.items,
      })
    })
    expect(listTenantEvalDatasets).toHaveBeenCalledTimes(2)
  })

  it("converts selected bad cases into an existing dataset", async () => {
    vi.mocked(listTenantBadCases).mockResolvedValue({
      items: badCases,
      total: badCases.length,
    })
    vi.mocked(convertBadCasesToEval).mockResolvedValue({
      dataset_id: "dataset-1",
      converted: 1,
      skipped: 0,
      items: [],
    })

    render(<EvaluationPage />)

    await userEvent.click(await screen.findByRole("button", { name: "从 Bad Case 转入" }))

    const dialog = await screen.findByRole("dialog", {
      name: "从 Bad Case 转入测评集",
    })
    await userEvent.click(
      within(dialog).getByRole("checkbox", { name: "选择 case-bad-1" }),
    )
    await userEvent.click(
      within(dialog).getByRole("combobox", { name: "目标测评集" }),
    )
    await userEvent.click(
      await screen.findByText("一期验收集", {
        selector: ".ant-select-item-option-content",
      }),
    )

    await userEvent.click(
      within(dialog).getByRole("button", { name: "转入测评集" }),
    )

    await waitFor(() => {
      expect(convertBadCasesToEval).toHaveBeenCalledWith("wx_acme", {
        case_ids: ["case-bad-1"],
        dataset_id: "dataset-1",
        dataset_name: "",
      })
    })
    await waitFor(() => {
      expect(vi.mocked(listTenantEvalDatasets).mock.calls.length).toBeGreaterThanOrEqual(2)
    })
  })

  it("submits bad case conversion only once on double click", async () => {
    const actualUseForm = Form.useForm.bind(Form)
    const validateDeferred = createDeferred<void>()
    const convertDeferred = createDeferred<{
      dataset_id: string
      converted: number
      skipped: number
      items: never[]
    }>()
    const validateFieldsSpy = vi.fn(
      async (
        originalValidateFields: () => Promise<{
          dataset_id?: string
          dataset_name?: string
        }>,
      ) => {
        await validateDeferred.promise
        return originalValidateFields()
      },
    )
    let useFormCallCount = 0
    const useFormSpy = vi.spyOn(Form, "useForm").mockImplementation(() => {
      const [form] = actualUseForm()
      useFormCallCount += 1
      if (useFormCallCount === 2) {
        const originalValidateFields = form.validateFields.bind(form)
        form.validateFields = vi.fn(() => validateFieldsSpy(originalValidateFields))
      }
      return [form]
    })
    vi.mocked(listTenantBadCases).mockResolvedValue({
      items: badCases,
      total: badCases.length,
    })
    vi.mocked(convertBadCasesToEval).mockImplementation(() => convertDeferred.promise)

    try {
      render(<EvaluationPage />)

      await userEvent.click(
        await screen.findByRole("button", { name: "从 Bad Case 转入" }),
      )

      const dialog = await screen.findByRole("dialog", {
        name: "从 Bad Case 转入测评集",
      })
      await userEvent.click(
        within(dialog).getByRole("checkbox", { name: "选择 case-bad-1" }),
      )
      await userEvent.click(
        within(dialog).getByRole("combobox", { name: "目标测评集" }),
      )
      await userEvent.click(
        await screen.findByText("一期验收集", {
          selector: ".ant-select-item-option-content",
        }),
      )

      const submitButton = within(dialog).getByRole("button", {
        name: "转入测评集",
      })
      await userEvent.dblClick(submitButton)

      await waitFor(() => {
        expect(validateFieldsSpy).toHaveBeenCalledTimes(1)
      })

      await act(async () => {
        validateDeferred.resolve()
        await Promise.resolve()
      })

      await waitFor(() => {
        expect(convertBadCasesToEval).toHaveBeenCalledTimes(1)
      })

      await act(async () => {
        convertDeferred.resolve({
          dataset_id: "dataset-1",
          converted: 1,
          skipped: 0,
          items: [],
        })
        await Promise.resolve()
      })
    } finally {
      useFormSpy.mockRestore()
    }
  })

  it("shows loaded execution count in execution tab", async () => {
    render(<EvaluationPage />)

    await userEvent.click(await screen.findByRole("tab", { name: "执行记录" }))

    expect(await screen.findByText("已加载 1 条执行记录")).toBeInTheDocument()
  })

  it("creates manual execution for selected dataset", async () => {
    vi.mocked(createTenantEvalExecution).mockResolvedValue({
      ...execution,
      id: "exec-created",
    })

    render(<EvaluationPage />)

    await userEvent.click(await screen.findByRole("tab", { name: "执行记录" }))
    await userEvent.click(
      await screen.findByRole("button", { name: "新建执行记录" }),
    )

    const dialog = await screen.findByRole("dialog", { name: "新建执行记录" })
    expect(dialog).toBeInTheDocument()

    await userEvent.click(within(dialog).getByRole("combobox", { name: "测评集" }))
    await userEvent.click(
      await screen.findByText("一期验收集", {
        selector: ".ant-select-item-option-content",
      }),
    )

    await userEvent.type(
      await within(dialog).findByRole("textbox", { name: "case-1 实际回答" }),
      "营收 100 万",
    )

    await userEvent.click(within(dialog).getByRole("combobox", { name: "case-1 结果" }))
    await userEvent.click(
      await screen.findByText("正确", {
        selector: ".ant-select-item-option-content",
      }),
    )

    await userEvent.click(
      within(dialog).getByRole("button", { name: "提交执行记录" }),
    )

    await waitFor(() => {
      expect(createTenantEvalExecution).toHaveBeenCalledWith("wx_acme", {
        dataset_id: "dataset-1",
        items: expect.arrayContaining([
          expect.objectContaining({
            case_id: "case-1",
            actual: "营收 100 万",
            result: "correct",
          }),
        ]),
      })
    })
    expect(listTenantEvalExecutions).toHaveBeenCalledTimes(2)
  })

  it("submits manual execution only once on double click", async () => {
    const actualUseForm = Form.useForm.bind(Form)
    const validateDeferred = createDeferred<void>()
    const executionDeferred = createDeferred<EvalExecution>()
    const validateFieldsSpy = vi.fn(async (originalValidateFields: () => Promise<{
      dataset_id: string
      cases?: Record<string, unknown>
    }>) => {
      await validateDeferred.promise
      return originalValidateFields()
    })
    const useFormSpy = vi.spyOn(Form, "useForm").mockImplementation(() => {
      const [form] = actualUseForm()
      const originalValidateFields = form.validateFields.bind(form)
      form.validateFields = vi.fn(() => validateFieldsSpy(originalValidateFields))
      return [form]
    })
    vi.mocked(createTenantEvalExecution).mockImplementation(
      () => executionDeferred.promise,
    )

    try {
      render(<EvaluationPage />)

      await userEvent.click(await screen.findByRole("tab", { name: "执行记录" }))
      await userEvent.click(
        await screen.findByRole("button", { name: "新建执行记录" }),
      )

      const dialog = await screen.findByRole("dialog", { name: "新建执行记录" })
      await userEvent.click(
        within(dialog).getByRole("combobox", { name: "测评集" }),
      )
      await userEvent.click(
        await screen.findByText("一期验收集", {
          selector: ".ant-select-item-option-content",
        }),
      )

      const submitButton = within(dialog).getByRole("button", {
        name: "提交执行记录",
      })
      await userEvent.dblClick(submitButton)

      await waitFor(() => {
        expect(validateFieldsSpy).toHaveBeenCalledTimes(1)
      })

      await act(async () => {
        validateDeferred.resolve()
        await Promise.resolve()
      })

      await waitFor(() => {
        expect(createTenantEvalExecution).toHaveBeenCalledTimes(1)
      })

      await act(async () => {
        executionDeferred.resolve(execution)
        await Promise.resolve()
      })
    } finally {
      useFormSpy.mockRestore()
    }
  })

  it("loads and renders accuracy report", async () => {
    vi.mocked(getTenantAccuracyReport).mockResolvedValue({
      dataset_id: "dataset-1",
      execution_id: "exec-1",
      total: 2,
      executable: 2,
      correct: 1,
      partial: 0,
      wrong: 1,
      blocked: 0,
      correct_rate: 0.5,
      partial_rate: 0,
      issue_distribution: { permission_config: 1 },
      created_at: "2026-05-13T10:00:00+00:00",
    })

    render(<EvaluationPage />)

    await userEvent.click(await screen.findByRole("tab", { name: "准确率报告" }))
    await userEvent.click(screen.getByRole("combobox", { name: "执行记录" }))
    await userEvent.click(
      await screen.findByText(/exec-1 \/ dataset-1 \//, {
        selector: ".ant-select-item-option-content",
      }),
    )
    await userEvent.click(screen.getByRole("button", { name: "查看报告" }))

    await waitFor(() => {
      expect(getTenantAccuracyReport).toHaveBeenCalledWith("wx_acme", "exec-1")
    })
    expect(
      await screen.findByText("正确率", {
        selector: ".ant-statistic-title",
      }),
    ).toBeInTheDocument()
    expect(screen.getByText("50.0%")).toBeInTheDocument()
    expect(screen.getByText("权限配置")).toBeInTheDocument()
  })

  it("exports tenant-scoped acceptance evidence", async () => {
    render(<EvaluationPage />)

    await userEvent.click(await screen.findByRole("tab", { name: "准确率报告" }))
    await userEvent.click(screen.getByRole("combobox", { name: "执行记录" }))
    await userEvent.click(
      await screen.findByText(/exec-1 \/ dataset-1 \//, {
        selector: ".ant-select-item-option-content",
      }),
    )
    await userEvent.click(screen.getByRole("button", { name: "导出证据" }))

    await waitFor(() => {
      expect(exportTenantAcceptanceEvidence).toHaveBeenCalledWith(
        "wx_acme",
        "exec-1",
      )
    })
    expect(await screen.findByText("验收证据")).toBeInTheDocument()
    expect(screen.getByText("版本：1")).toBeInTheDocument()
    expect(screen.getByText("租户：acme / wx_acme")).toBeInTheDocument()
    expect(screen.getByText("执行：exec-1")).toBeInTheDocument()
  })

  it("does not show stale report after switching execution selection", async () => {
    const reportDeferred = createDeferred<AccuracyReport>()

    vi.mocked(listTenantEvalExecutions).mockResolvedValue({
      items: [execution, secondExecution],
      total: 2,
    })
    vi.mocked(getTenantAccuracyReport).mockImplementationOnce(
      () => reportDeferred.promise,
    )

    render(<EvaluationPage />)

    await userEvent.click(await screen.findByRole("tab", { name: "准确率报告" }))
    await userEvent.click(screen.getByRole("combobox", { name: "执行记录" }))
    await userEvent.click(
      await screen.findByText(/exec-1 \/ dataset-1 \//, {
        selector: ".ant-select-item-option-content",
      }),
    )
    await userEvent.click(screen.getByRole("button", { name: "查看报告" }))

    await waitFor(() => {
      expect(getTenantAccuracyReport).toHaveBeenCalledWith("wx_acme", "exec-1")
    })

    await userEvent.click(screen.getByRole("combobox", { name: "执行记录" }))
    await userEvent.click(
      await screen.findByText(/exec-2 \/ dataset-1 \//, {
        selector: ".ant-select-item-option-content",
      }),
    )

    await act(async () => {
      reportDeferred.resolve({
        dataset_id: "dataset-1",
        execution_id: "exec-1",
        total: 1,
        executable: 1,
        correct: 1,
        partial: 0,
        wrong: 0,
        blocked: 0,
        correct_rate: 1,
        partial_rate: 0,
        issue_distribution: {},
        created_at: "2026-05-13T09:00:00+00:00",
      })
      await Promise.resolve()
    })

    await waitFor(() => {
      expect(screen.getByText("请选择执行记录并查看报告")).toBeInTheDocument()
    })
    expect(screen.queryByText("100.0%")).not.toBeInTheDocument()
  })

  it("does not show stale report error after switching execution selection", async () => {
    const reportDeferred = createDeferred<AccuracyReport>()

    vi.mocked(listTenantEvalExecutions).mockResolvedValue({
      items: [execution, secondExecution],
      total: 2,
    })
    vi.mocked(getTenantAccuracyReport).mockImplementationOnce(
      () => reportDeferred.promise,
    )

    render(<EvaluationPage />)

    await userEvent.click(await screen.findByRole("tab", { name: "准确率报告" }))
    await userEvent.click(screen.getByRole("combobox", { name: "执行记录" }))
    await userEvent.click(
      await screen.findByText(/exec-1 \/ dataset-1 \//, {
        selector: ".ant-select-item-option-content",
      }),
    )
    await userEvent.click(screen.getByRole("button", { name: "查看报告" }))

    await waitFor(() => {
      expect(getTenantAccuracyReport).toHaveBeenCalledWith("wx_acme", "exec-1")
    })

    await userEvent.click(screen.getByRole("combobox", { name: "执行记录" }))
    await userEvent.click(
      await screen.findByText(/exec-2 \/ dataset-1 \//, {
        selector: ".ant-select-item-option-content",
      }),
    )

    await act(async () => {
      reportDeferred.reject(new Error("旧报告失败"))
      await Promise.resolve()
    })

    expect(screen.getByText("请选择执行记录并查看报告")).toBeInTheDocument()
    expect(messageErrorSpy).not.toHaveBeenCalled()
  })

  it("does not let stale tenant response override current tenant data", async () => {
    const firstDatasetDeferred = createDeferred<{ items: EvalDataset[]; total: number }>()
    const firstExecutionDeferred = createDeferred<{
      items: EvalExecution[]
      total: number
    }>()

    vi.mocked(listWecomTenants).mockResolvedValue({
      tenants: [tenant, secondTenant],
    })
    vi.mocked(listTenantEvalDatasets)
      .mockImplementationOnce(() => firstDatasetDeferred.promise)
      .mockResolvedValueOnce({ items: [secondDataset], total: 1 })
    vi.mocked(listTenantEvalExecutions)
      .mockImplementationOnce(() => firstExecutionDeferred.promise)
      .mockResolvedValueOnce({ items: [], total: 0 })

    render(<EvaluationPage />)

    await screen.findByText("acme / wx_acme")
    await userEvent.click(screen.getByRole("combobox", { name: "租户选择器" }))
    await userEvent.click(await screen.findByText("beta / wx_beta"))

    expect(screen.queryByText("一期验收集")).not.toBeInTheDocument()
    expect(await screen.findByText("二期验收集")).toBeInTheDocument()

    await act(async () => {
      firstDatasetDeferred.resolve({ items: [dataset], total: 1 })
      firstExecutionDeferred.resolve({ items: [execution], total: 1 })
      await Promise.resolve()
    })

    await waitFor(() => {
      expect(screen.getByText("二期验收集")).toBeInTheDocument()
    })
    expect(screen.queryByText("一期验收集")).not.toBeInTheDocument()
  })

  it("clears report loading and ignores stale report after tenant switch", async () => {
    const reportDeferred = createDeferred<AccuracyReport>()

    vi.mocked(listWecomTenants).mockResolvedValue({
      tenants: [tenant, secondTenant],
    })
    vi.mocked(listTenantEvalDatasets)
      .mockResolvedValueOnce({ items: [dataset], total: 1 })
      .mockResolvedValueOnce({ items: [secondDataset], total: 1 })
    vi.mocked(listTenantEvalExecutions)
      .mockResolvedValueOnce({ items: [execution], total: 1 })
      .mockResolvedValueOnce({ items: [], total: 0 })
    vi.mocked(getTenantAccuracyReport).mockImplementationOnce(
      () => reportDeferred.promise,
    )

    render(<EvaluationPage />)

    await userEvent.click(await screen.findByRole("tab", { name: "准确率报告" }))
    await userEvent.click(screen.getByRole("combobox", { name: "执行记录" }))
    await userEvent.click(
      await screen.findByText(/exec-1 \/ dataset-1 \//, {
        selector: ".ant-select-item-option-content",
      }),
    )
    await userEvent.click(screen.getByRole("button", { name: "查看报告" }))

    await waitFor(() => {
      expect(getTenantAccuracyReport).toHaveBeenCalledWith("wx_acme", "exec-1")
    })

    await userEvent.click(screen.getByRole("combobox", { name: "租户选择器" }))
    await userEvent.click(await screen.findByText("beta / wx_beta"))

    await userEvent.click(await screen.findByRole("tab", { name: "准确率报告" }))

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "查看报告" })).not.toBeDisabled()
    })

    await act(async () => {
      reportDeferred.resolve({
        dataset_id: "dataset-1",
        execution_id: "exec-1",
        total: 1,
        executable: 1,
        correct: 1,
        partial: 0,
        wrong: 0,
        blocked: 0,
        correct_rate: 1,
        partial_rate: 0,
        issue_distribution: {},
        created_at: "2026-05-13T09:00:00+00:00",
      })
      await Promise.resolve()
    })

    await waitFor(() => {
      expect(screen.getByText("请选择执行记录并查看报告")).toBeInTheDocument()
    })
    expect(screen.queryByText("100.0%")).not.toBeInTheDocument()
  })

  it("creates dataset from sample only once on double click", async () => {
    const sampleDeferred = createDeferred<EvalDataset>()
    const createDatasetDeferred = createDeferred<EvalDataset>()
    vi.mocked(getSampleEvalDataset).mockImplementation(() => sampleDeferred.promise)
    vi.mocked(createTenantEvalDataset).mockImplementation(
      () => createDatasetDeferred.promise,
    )

    render(<EvaluationPage />)

    const button = await screen.findByRole("button", { name: "从样例创建" })
    await userEvent.dblClick(button)

    await waitFor(() => {
      expect(getSampleEvalDataset).toHaveBeenCalledTimes(1)
    })
    expect(createTenantEvalDataset).toHaveBeenCalledTimes(0)

    await act(async () => {
      sampleDeferred.resolve(dataset)
      await Promise.resolve()
    })

    await waitFor(() => {
      expect(createTenantEvalDataset).toHaveBeenCalledTimes(1)
    })

    await act(async () => {
      createDatasetDeferred.resolve(dataset)
      await Promise.resolve()
    })

    expect(createTenantEvalDataset).toHaveBeenCalledWith("wx_acme", {
      name: dataset.name,
      description: dataset.description,
      items: dataset.items,
    })
  })

  it("keeps datasets when execution request fails", async () => {
    vi.mocked(listTenantEvalExecutions).mockRejectedValue(new Error("执行记录挂了"))

    render(<EvaluationPage />)

    expect(await screen.findByText("一期验收集")).toBeInTheDocument()
    await userEvent.click(screen.getByRole("tab", { name: "执行记录" }))
    expect(await screen.findByText("已加载 0 条执行记录")).toBeInTheDocument()
    expect(messageErrorSpy).toHaveBeenCalledWith("执行记录挂了")
  })

  it("does not reload old tenant after sample creation resolves during tenant switch", async () => {
    const createDatasetDeferred = createDeferred<EvalDataset>()

    vi.mocked(listWecomTenants).mockResolvedValue({
      tenants: [tenant, secondTenant],
    })
    vi.mocked(createTenantEvalDataset).mockImplementation(
      () => createDatasetDeferred.promise,
    )
    vi.mocked(listTenantEvalDatasets)
      .mockResolvedValueOnce({ items: [dataset], total: 1 })
      .mockResolvedValueOnce({ items: [secondDataset], total: 1 })
    vi.mocked(listTenantEvalExecutions)
      .mockResolvedValueOnce({ items: [execution], total: 1 })
      .mockResolvedValueOnce({ items: [], total: 0 })

    render(<EvaluationPage />)

    expect(await screen.findByText("一期验收集")).toBeInTheDocument()
    await userEvent.click(screen.getByRole("button", { name: "从样例创建" }))

    await userEvent.click(screen.getByRole("combobox", { name: "租户选择器" }))
    await userEvent.click(await screen.findByText("beta / wx_beta"))

    expect(await screen.findByText("二期验收集")).toBeInTheDocument()
    expect(screen.queryByText("一期验收集")).not.toBeInTheDocument()

    await act(async () => {
      createDatasetDeferred.resolve(dataset)
      await Promise.resolve()
    })

    await waitFor(() => {
      expect(screen.getByText("二期验收集")).toBeInTheDocument()
    })
    expect(screen.queryByText("一期验收集")).not.toBeInTheDocument()
    expect(listTenantEvalDatasets).toHaveBeenCalledTimes(2)
  })

  it("ignores stale bad case submit resolve after tenant switch", async () => {
    const firstConvertDeferred = createDeferred<{
      dataset_id: string
      converted: number
      skipped: number
      items: never[]
    }>()
    const secondConvertDeferred = createDeferred<{
      dataset_id: string
      converted: number
      skipped: number
      items: never[]
    }>()

    vi.mocked(listWecomTenants).mockResolvedValue({
      tenants: [tenant, secondTenant],
    })
    vi.mocked(listTenantBadCases).mockResolvedValue({
      items: badCases,
      total: badCases.length,
    })
    vi.mocked(listTenantEvalDatasets)
      .mockResolvedValueOnce({ items: [dataset], total: 1 })
      .mockResolvedValueOnce({ items: [secondDataset], total: 1 })
    vi.mocked(listTenantEvalExecutions)
      .mockResolvedValueOnce({ items: [execution], total: 1 })
      .mockResolvedValueOnce({ items: [], total: 0 })
    vi.mocked(convertBadCasesToEval)
      .mockImplementationOnce(() => firstConvertDeferred.promise)
      .mockImplementationOnce(() => secondConvertDeferred.promise)

    render(<EvaluationPage />)

    expect(await screen.findByText("一期验收集")).toBeInTheDocument()
    await userEvent.click(screen.getByRole("button", { name: "从 Bad Case 转入" }))

    const firstDialog = await screen.findByRole("dialog", {
      name: "从 Bad Case 转入测评集",
    })
    await userEvent.click(
      within(firstDialog).getByRole("checkbox", { name: "选择 case-bad-1" }),
    )
    await userEvent.click(
      within(firstDialog).getByRole("combobox", { name: "目标测评集" }),
    )
    await userEvent.click(
      await screen.findByText("一期验收集", {
        selector: ".ant-select-item-option-content",
      }),
    )
    await userEvent.click(
      within(firstDialog).getByRole("button", { name: "转入测评集" }),
    )

    await waitFor(() => {
      expect(convertBadCasesToEval).toHaveBeenCalledWith("wx_acme", {
        case_ids: ["case-bad-1"],
        dataset_id: "dataset-1",
        dataset_name: "",
      })
    })

    await userEvent.click(screen.getByRole("combobox", { name: "租户选择器" }))
    await userEvent.click(await screen.findByText("beta / wx_beta"))

    expect(await screen.findByText("二期验收集")).toBeInTheDocument()
    expect(screen.queryByText("一期验收集")).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole("button", { name: "从 Bad Case 转入" }))
    const secondDialog = await screen.findByRole("dialog", {
      name: "从 Bad Case 转入测评集",
    })
    await userEvent.click(
      within(secondDialog).getByRole("checkbox", { name: "选择 case-bad-1" }),
    )
    await userEvent.click(
      within(secondDialog).getByRole("combobox", { name: "目标测评集" }),
    )
    await userEvent.click(
      await screen.findByText("二期验收集", {
        selector: ".ant-select-item-option-content",
      }),
    )
    await userEvent.click(
      within(secondDialog).getByRole("button", { name: "转入测评集" }),
    )

    await waitFor(() => {
      expect(convertBadCasesToEval).toHaveBeenNthCalledWith(2, "wx_beta", {
        case_ids: ["case-bad-1"],
        dataset_id: "dataset-2",
        dataset_name: "",
      })
    })

    await act(async () => {
      firstConvertDeferred.resolve({
        dataset_id: "dataset-1",
        converted: 1,
        skipped: 0,
        items: [],
      })
      await Promise.resolve()
    })

    expect(messageSuccessSpy).not.toHaveBeenCalledWith("已转入 1 条，跳过 0 条")

    const secondSubmitButton = within(secondDialog).getByRole("button", {
      name: /转入测评集/,
    })
    await userEvent.click(secondSubmitButton)
    expect(convertBadCasesToEval).toHaveBeenCalledTimes(2)

    await act(async () => {
      secondConvertDeferred.resolve({
        dataset_id: "dataset-2",
        converted: 1,
        skipped: 0,
        items: [],
      })
      await Promise.resolve()
    })
  })

  it("ignores stale bad case submit error after tenant switch", async () => {
    const convertDeferred = createDeferred<{
      dataset_id: string
      converted: number
      skipped: number
      items: never[]
    }>()

    vi.mocked(listWecomTenants).mockResolvedValue({
      tenants: [tenant, secondTenant],
    })
    vi.mocked(listTenantBadCases).mockResolvedValue({
      items: badCases,
      total: badCases.length,
    })
    vi.mocked(listTenantEvalDatasets)
      .mockResolvedValueOnce({ items: [dataset], total: 1 })
      .mockResolvedValueOnce({ items: [secondDataset], total: 1 })
    vi.mocked(listTenantEvalExecutions)
      .mockResolvedValueOnce({ items: [execution], total: 1 })
      .mockResolvedValueOnce({ items: [], total: 0 })
    vi.mocked(convertBadCasesToEval).mockImplementation(() => convertDeferred.promise)

    render(<EvaluationPage />)

    await screen.findByText("一期验收集")
    await userEvent.click(screen.getByRole("button", { name: "从 Bad Case 转入" }))

    const dialog = await screen.findByRole("dialog", {
      name: "从 Bad Case 转入测评集",
    })
    await userEvent.click(
      within(dialog).getByRole("checkbox", { name: "选择 case-bad-1" }),
    )
    await userEvent.click(
      within(dialog).getByRole("combobox", { name: "目标测评集" }),
    )
    await userEvent.click(
      await screen.findByText("一期验收集", {
        selector: ".ant-select-item-option-content",
      }),
    )
    await userEvent.click(
      within(dialog).getByRole("button", { name: "转入测评集" }),
    )

    await waitFor(() => {
      expect(convertBadCasesToEval).toHaveBeenCalledWith("wx_acme", {
        case_ids: ["case-bad-1"],
        dataset_id: "dataset-1",
        dataset_name: "",
      })
    })

    await userEvent.click(screen.getByRole("combobox", { name: "租户选择器" }))
    await userEvent.click(await screen.findByText("beta / wx_beta"))

    expect(await screen.findByText("二期验收集")).toBeInTheDocument()

    await act(async () => {
      convertDeferred.reject(new Error("旧提交失败"))
      await Promise.resolve()
    })

    expect(messageErrorSpy).not.toHaveBeenCalledWith("旧提交失败")
    await userEvent.click(await screen.findByRole("button", { name: "从 Bad Case 转入" }))
    const nextDialog = await screen.findByRole("dialog", {
      name: "从 Bad Case 转入测评集",
    })
    expect(
      within(nextDialog).getByRole("button", { name: "转入测评集" }),
    ).not.toBeDisabled()
  })

  it("does not show internal page completeness details", async () => {
    render(<EvaluationPage />)

    expect(await screen.findByRole("heading", { name: "验收测评" })).toBeInTheDocument()
    expect(screen.queryByText("页面完整性")).not.toBeInTheDocument()
    expect(screen.queryByText("Console 退出关系")).not.toBeInTheDocument()
  })

  it("shows staged automation and export notes", async () => {
    render(<EvaluationPage />)

    expect(
      await screen.findByText(/自动问答回放、LLM 判分、跨租户聚合和正式报告文件导出/),
    ).toBeInTheDocument()
    expect(screen.getByText(/租户级验收证据生成与摘要预览/)).toBeInTheDocument()
  })
})
