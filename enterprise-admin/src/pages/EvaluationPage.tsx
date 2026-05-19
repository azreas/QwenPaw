import React, { useCallback, useEffect, useMemo, useRef, useState } from "react"
import {
  Alert,
  Button,
  Card,
  type CheckboxProps,
  Col,
  Drawer,
  Empty,
  Form,
  Input,
  Modal,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tabs,
  Typography,
  message,
} from "antd"
import type { ColumnsType } from "antd/es/table"
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
import { listTenantBadCases } from "@/api/ops"
import { listWecomTenants } from "@/api/tenants"
import type {
  AcceptanceEvidenceExport,
  AccuracyReport,
  BadCaseItem,
  EvalDataset,
  EvalExecution,
  EvalItem,
  WecomTenantSummary,
} from "@/api/types"
import {
  EVAL_ACTION_OPTIONS,
  EVAL_ENTRYPOINT_OPTIONS,
  EVAL_ISSUE_OWNER_OPTIONS,
  EVAL_RESULT_OPTIONS,
  ManualExecutionValues,
  buildExecutionPayload,
  buildExecutionStats,
  buildDatasetStats,
  formatAccuracyRate,
  getEvalCategoryLabel,
  getIssueOwnerLabel,
} from "@/features/evaluation/evaluationModel"
import PageCompletenessPanel from "@/features/platform-readiness/PageCompletenessPanel"

const { Title, Text } = Typography
const { TextArea } = Input

type ExecutionFormValues = {
  dataset_id: string
  cases?: ManualExecutionValues
}

type BadCaseConvertFormValues = {
  dataset_id?: string
  dataset_name?: string
}

const ENTRYPOINT_LABELS = Object.fromEntries(
  EVAL_ENTRYPOINT_OPTIONS.map((item) => [item.value, item.label]),
) as Record<string, string>

function formatDateTime(value?: string | null): string {
  if (!value) {
    return "-"
  }
  return new Date(value).toLocaleString()
}

const EvaluationPage: React.FC = () => {
  const [tenants, setTenants] = useState<WecomTenantSummary[]>([])
  const [selectedAgentId, setSelectedAgentId] = useState<string>()
  const [datasets, setDatasets] = useState<EvalDataset[]>([])
  const [executions, setExecutions] = useState<EvalExecution[]>([])
  const [tenantLoading, setTenantLoading] = useState(true)
  const [dataLoading, setDataLoading] = useState(false)
  const [createLoading, setCreateLoading] = useState(false)
  const [executionModalOpen, setExecutionModalOpen] = useState(false)
  const [executionSaving, setExecutionSaving] = useState(false)
  const [badCaseModalOpen, setBadCaseModalOpen] = useState(false)
  const [badCases, setBadCases] = useState<BadCaseItem[]>([])
  const [selectedBadCaseIds, setSelectedBadCaseIds] = useState<React.Key[]>([])
  const [badCaseLoading, setBadCaseLoading] = useState(false)
  const [badCaseSubmitting, setBadCaseSubmitting] = useState(false)
  const [selectedExecutionId, setSelectedExecutionId] = useState<string>()
  const [report, setReport] = useState<AccuracyReport | null>(null)
  const [reportLoading, setReportLoading] = useState(false)
  const [evidence, setEvidence] = useState<AcceptanceEvidenceExport | null>(null)
  const [evidenceLoading, setEvidenceLoading] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [activeDataset, setActiveDataset] = useState<EvalDataset | null>(null)
  const [executionForm] = Form.useForm<ExecutionFormValues>()
  const [badCaseForm] = Form.useForm<BadCaseConvertFormValues>()
  const requestSeqRef = useRef(0)
  const badCaseRequestSeqRef = useRef(0)
  const badCaseSubmitSeqRef = useRef(0)
  const reportRequestSeqRef = useRef(0)
  const evidenceRequestSeqRef = useRef(0)
  const createLoadingRef = useRef(false)
  const executionSavingRef = useRef(false)
  const badCaseSubmittingRef = useRef(false)
  const selectedAgentIdRef = useRef<string | undefined>(undefined)
  const selectedExecutionIdRef = useRef<string | undefined>(undefined)
  const selectedDatasetId = Form.useWatch("dataset_id", executionForm)
  const selectedBadCaseDatasetId = Form.useWatch("dataset_id", badCaseForm)

  useEffect(() => {
    selectedAgentIdRef.current = selectedAgentId
  }, [selectedAgentId])

  useEffect(() => {
    selectedExecutionIdRef.current = selectedExecutionId
  }, [selectedExecutionId])

  useEffect(() => {
    setExecutionModalOpen(false)
    executionForm.resetFields()
    setBadCaseModalOpen(false)
    setBadCases([])
    setSelectedBadCaseIds([])
    setBadCaseLoading(false)
    badCaseSubmitSeqRef.current += 1
    setBadCaseSubmitting(false)
    badCaseSubmittingRef.current = false
    badCaseForm.resetFields()
    selectedExecutionIdRef.current = undefined
    setSelectedExecutionId(undefined)
    setReport(null)
    setReportLoading(false)
    setEvidence(null)
    setEvidenceLoading(false)
    evidenceRequestSeqRef.current += 1
  }, [badCaseForm, executionForm, selectedAgentId])

  const loadEvaluationData = useCallback(async (agentId: string) => {
    const requestSeq = ++requestSeqRef.current
    setDataLoading(true)
    setDatasets([])
    setExecutions([])
    try {
      const [datasetResponse, executionResponse] = await Promise.allSettled([
        listTenantEvalDatasets(agentId),
        listTenantEvalExecutions(agentId, {}),
      ])
      if (requestSeq !== requestSeqRef.current) {
        return
      }
      if (datasetResponse.status === "fulfilled") {
        setDatasets(datasetResponse.value.items)
      } else {
        setDatasets([])
        message.error(
          datasetResponse.reason instanceof Error
            ? datasetResponse.reason.message
            : "加载测评集失败",
        )
      }
      if (executionResponse.status === "fulfilled") {
        setExecutions(executionResponse.value.items)
      } else {
        setExecutions([])
        message.error(
          executionResponse.reason instanceof Error
            ? executionResponse.reason.message
            : "加载执行记录失败",
        )
      }
    } finally {
      if (requestSeq === requestSeqRef.current) {
        setDataLoading(false)
      }
    }
  }, [])

  const loadTenants = useCallback(async () => {
    try {
      setTenantLoading(true)
      const response = await listWecomTenants()
      const nextTenants = response.tenants
      setTenants(nextTenants)
      if (nextTenants.length === 0) {
        selectedAgentIdRef.current = undefined
        setSelectedAgentId(undefined)
        setDatasets([])
        setExecutions([])
        return
      }
      setSelectedAgentId((current) => {
        if (current && nextTenants.some((item) => item.agent_id === current)) {
          return current
        }
        return nextTenants[0].agent_id
      })
    } catch (err) {
      setTenants([])
      selectedAgentIdRef.current = undefined
      setSelectedAgentId(undefined)
      setDatasets([])
      setExecutions([])
      message.error(err instanceof Error ? err.message : "加载租户列表失败")
    } finally {
      setTenantLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadTenants()
  }, [loadTenants])

  useEffect(() => {
    if (!selectedAgentId) {
      return
    }
    void loadEvaluationData(selectedAgentId)
  }, [loadEvaluationData, selectedAgentId])

  const stats = useMemo(() => buildDatasetStats(datasets), [datasets])
  const datasetMap = useMemo(
    () => new Map(datasets.map((item) => [item.id, item])),
    [datasets],
  )
  const selectedDataset = selectedDatasetId
    ? datasetMap.get(selectedDatasetId) ?? null
    : null
  const reportIssueRows = useMemo(
    () =>
      Object.entries(report?.issue_distribution ?? {}).map(([key, count]) => ({
        key,
        issue_owner: key,
        count,
      })),
    [report],
  )

  const handleTenantChange = (agentId: string) => {
    selectedAgentIdRef.current = agentId
    requestSeqRef.current += 1
    badCaseRequestSeqRef.current += 1
    badCaseSubmitSeqRef.current += 1
    reportRequestSeqRef.current += 1
    evidenceRequestSeqRef.current += 1
    selectedExecutionIdRef.current = undefined
    setSelectedAgentId(agentId)
    setDatasets([])
    setExecutions([])
    setDataLoading(true)
    setSelectedExecutionId(undefined)
    setReport(null)
    setReportLoading(false)
    setEvidence(null)
    setEvidenceLoading(false)
    setExecutionModalOpen(false)
    executionForm.resetFields()
    setBadCaseModalOpen(false)
    setBadCases([])
    setSelectedBadCaseIds([])
    setBadCaseLoading(false)
    setBadCaseSubmitting(false)
    badCaseSubmittingRef.current = false
    badCaseForm.resetFields()
  }

  const handleCreateFromSample = async () => {
    if (createLoading || createLoadingRef.current) return
    const tenantAtStart = selectedAgentIdRef.current
    if (!tenantAtStart) return
    setCreateLoading(true)
    createLoadingRef.current = true
    try {
      const sample = await getSampleEvalDataset()
      await createTenantEvalDataset(tenantAtStart, {
        name: sample.name,
        description: sample.description,
        items: sample.items,
      })
      message.success("样例测评集已创建")
      if (
        tenantAtStart &&
        tenantAtStart === selectedAgentIdRef.current
      ) {
        await loadEvaluationData(tenantAtStart)
      }
    } catch (err) {
      message.error(err instanceof Error ? err.message : "创建样例测评集失败")
    } finally {
      setCreateLoading(false)
      createLoadingRef.current = false
    }
  }

  const handleOpenDrawer = (dataset: EvalDataset) => {
    setActiveDataset(dataset)
    setDrawerOpen(true)
  }

  const handleOpenExecutionModal = () => {
    executionForm.resetFields()
    setExecutionModalOpen(true)
  }

  const handleOpenBadCaseModal = async () => {
    if (badCaseLoading) return
    const tenantAtStart = selectedAgentIdRef.current
    if (!tenantAtStart) return
    const requestSeq = ++badCaseRequestSeqRef.current
    setBadCaseLoading(true)
    try {
      const response = await listTenantBadCases(tenantAtStart)
      if (
        requestSeq !== badCaseRequestSeqRef.current ||
        tenantAtStart !== selectedAgentIdRef.current
      ) {
        return
      }
      setBadCases(response.items)
      setSelectedBadCaseIds([])
      badCaseForm.resetFields()
      setBadCaseModalOpen(true)
    } catch (err) {
      if (
        requestSeq === badCaseRequestSeqRef.current &&
        tenantAtStart === selectedAgentIdRef.current
      ) {
        message.error(err instanceof Error ? err.message : "加载 Bad Case 失败")
      }
    } finally {
      if (
        requestSeq === badCaseRequestSeqRef.current &&
        tenantAtStart === selectedAgentIdRef.current
      ) {
        setBadCaseLoading(false)
      }
    }
  }

  const handleCloseExecutionModal = () => {
    if (executionSaving || executionSavingRef.current) return
    setExecutionModalOpen(false)
    executionForm.resetFields()
  }

  const handleCloseBadCaseModal = () => {
    if (badCaseSubmitting || badCaseSubmittingRef.current) return
    badCaseSubmitSeqRef.current += 1
    setBadCaseModalOpen(false)
    setSelectedBadCaseIds([])
    setBadCaseSubmitting(false)
    badCaseSubmittingRef.current = false
    badCaseForm.resetFields()
  }

  const handleSubmitExecution = async () => {
    if (executionSaving || executionSavingRef.current) return
    const tenantAtStart = selectedAgentIdRef.current
    if (!tenantAtStart) return
    executionSavingRef.current = true
    setExecutionSaving(true)
    try {
      const values = await executionForm.validateFields()
      const targetDataset = datasetMap.get(values.dataset_id)
      if (!targetDataset) {
        message.error("请选择测评集")
        return
      }
      await createTenantEvalExecution(
        tenantAtStart,
        buildExecutionPayload(targetDataset, values.cases || {}),
      )
      message.success("执行记录已提交")
      if (tenantAtStart === selectedAgentIdRef.current) {
        setExecutionModalOpen(false)
        executionForm.resetFields()
        await loadEvaluationData(tenantAtStart)
      }
    } catch (err) {
      if (err instanceof Error) {
        message.error(err.message)
      }
    } finally {
      executionSavingRef.current = false
      setExecutionSaving(false)
    }
  }

  const handleExecutionSelectionChange = (nextExecutionId: string) => {
    selectedExecutionIdRef.current = nextExecutionId
    reportRequestSeqRef.current += 1
    evidenceRequestSeqRef.current += 1
    setSelectedExecutionId(nextExecutionId)
    setReport(null)
    setReportLoading(false)
    setEvidence(null)
    setEvidenceLoading(false)
  }

  const handleSubmitBadCases = async () => {
    if (badCaseSubmitting || badCaseSubmittingRef.current) return
    const tenantAtStart = selectedAgentIdRef.current
    if (!tenantAtStart) return
    if (selectedBadCaseIds.length === 0) {
      message.error("请选择 Bad Case")
      return
    }
    const caseIdsAtStart = selectedBadCaseIds.map((item) => String(item))
    const submitSeq = ++badCaseSubmitSeqRef.current
    const isCurrentSubmit = () =>
      submitSeq === badCaseSubmitSeqRef.current &&
      tenantAtStart === selectedAgentIdRef.current
    badCaseSubmittingRef.current = true
    setBadCaseSubmitting(true)
    try {
      const values = await badCaseForm.validateFields()
      if (!isCurrentSubmit()) {
        return
      }
      const datasetId = values.dataset_id?.trim()
      const datasetName = values.dataset_name?.trim() ?? ""
      if (!datasetId && !datasetName) {
        message.error("请选择目标测评集或填写新测评集名称")
        return
      }
      const result = await convertBadCasesToEval(tenantAtStart, {
        case_ids: caseIdsAtStart,
        dataset_id: datasetId || null,
        dataset_name: datasetId ? "" : datasetName,
      })
      if (isCurrentSubmit()) {
        message.success(`已转入 ${result.converted} 条，跳过 ${result.skipped} 条`)
        setBadCaseModalOpen(false)
        setSelectedBadCaseIds([])
        badCaseForm.resetFields()
        await loadEvaluationData(tenantAtStart)
      }
    } catch (err) {
      if (isCurrentSubmit()) {
        if (err instanceof Error) {
          message.error(err.message)
        } else {
          message.error("Bad Case 转入失败")
        }
      }
    } finally {
      if (isCurrentSubmit()) {
        badCaseSubmittingRef.current = false
        setBadCaseSubmitting(false)
      }
    }
  }

  const handleLoadReport = async () => {
    if (!selectedAgentId) return
    if (!selectedExecutionId) {
      message.warning("请选择执行记录")
      return
    }
    const tenantAtStart = selectedAgentId
    const executionIdAtStart = selectedExecutionId
    const reportRequestSeq = ++reportRequestSeqRef.current
    const isCurrentReportRequest = () =>
      reportRequestSeq === reportRequestSeqRef.current &&
      tenantAtStart === selectedAgentIdRef.current &&
      executionIdAtStart === selectedExecutionIdRef.current
    try {
      setReportLoading(true)
      const nextReport = await getTenantAccuracyReport(
        tenantAtStart,
        executionIdAtStart,
      )
      if (isCurrentReportRequest()) {
        setReport(nextReport)
      }
    } catch (err) {
      if (isCurrentReportRequest()) {
        message.error(err instanceof Error ? err.message : "加载准确率报告失败")
      }
    } finally {
      if (isCurrentReportRequest()) {
        setReportLoading(false)
      }
    }
  }

  const handleExportEvidence = async () => {
    if (!selectedAgentId) return
    if (!selectedExecutionId) {
      message.warning("请选择执行记录")
      return
    }
    const tenantAtStart = selectedAgentId
    const executionIdAtStart = selectedExecutionId
    const evidenceRequestSeq = ++evidenceRequestSeqRef.current
    const isCurrentEvidenceRequest = () =>
      evidenceRequestSeq === evidenceRequestSeqRef.current &&
      tenantAtStart === selectedAgentIdRef.current &&
      executionIdAtStart === selectedExecutionIdRef.current
    try {
      setEvidenceLoading(true)
      const nextEvidence = await exportTenantAcceptanceEvidence(
        tenantAtStart,
        executionIdAtStart,
      )
      if (isCurrentEvidenceRequest()) {
        setEvidence(nextEvidence)
        message.success("验收证据已生成")
      }
    } catch (err) {
      if (isCurrentEvidenceRequest()) {
        message.error(err instanceof Error ? err.message : "导出验收证据失败")
      }
    } finally {
      if (isCurrentEvidenceRequest()) {
        setEvidenceLoading(false)
      }
    }
  }

  const handleCloseDrawer = () => {
    setDrawerOpen(false)
    setActiveDataset(null)
  }

  const datasetColumns: ColumnsType<EvalDataset> = [
    {
      title: "名称",
      dataIndex: "name",
      key: "name",
    },
    {
      title: "题目数",
      key: "count",
      render: (_, record) => record.items.length,
    },
    {
      title: "描述",
      dataIndex: "description",
      key: "description",
      render: (value?: string) => value || "-",
    },
    {
      title: "更新时间",
      dataIndex: "updated_at",
      key: "updated_at",
      render: (value?: string | null) => formatDateTime(value),
    },
    {
      title: "操作",
      key: "action",
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          aria-label={`查看题目 ${record.name}`}
          onClick={() => handleOpenDrawer(record)}
        >
          查看题目
        </Button>
      ),
    },
  ]

  const itemColumns: ColumnsType<EvalItem> = [
    {
      title: "Case ID",
      dataIndex: "case_id",
      key: "case_id",
    },
    {
      title: "分类",
      dataIndex: "category",
      key: "category",
      render: (value: string) => getEvalCategoryLabel(value),
    },
    {
      title: "问题",
      dataIndex: "question",
      key: "question",
    },
    {
      title: "预期",
      dataIndex: "expected",
      key: "expected",
    },
    {
      title: "入口",
      dataIndex: "entrypoint",
      key: "entrypoint",
      render: (value: string) => ENTRYPOINT_LABELS[value] || value,
    },
    {
      title: "能力",
      dataIndex: "ability",
      key: "ability",
      render: (value?: string) => value || "-",
    },
    {
      title: "负责人",
      dataIndex: "owner",
      key: "owner",
      render: (value?: string) => getIssueOwnerLabel(value),
    },
  ]

  const executionColumns: ColumnsType<EvalExecution> = [
    {
      title: "执行 ID",
      dataIndex: "id",
      key: "id",
    },
    {
      title: "测评集",
      dataIndex: "dataset_id",
      key: "dataset_id",
      render: (value: string) => datasetMap.get(value)?.name || value,
    },
    {
      title: "题目数",
      key: "count",
      render: (_, record) => buildExecutionStats([record]).totalExecutedItems,
    },
    {
      title: "正确",
      key: "correct",
      render: (_, record) => buildExecutionStats([record]).correctItems,
    },
    {
      title: "部分正确",
      key: "partial",
      render: (_, record) => buildExecutionStats([record]).partialItems,
    },
    {
      title: "错误",
      key: "wrong",
      render: (_, record) => buildExecutionStats([record]).wrongItems,
    },
    {
      title: "阻塞",
      key: "blocked",
      render: (_, record) => buildExecutionStats([record]).blockedItems,
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      key: "created_at",
      render: (value?: string | null) => formatDateTime(value),
    },
  ]

  const badCaseColumns: ColumnsType<BadCaseItem> = [
    {
      title: "Case ID",
      dataIndex: "case_id",
      key: "case_id",
    },
    {
      title: "分类",
      dataIndex: "category",
      key: "category",
    },
    {
      title: "能力",
      key: "ability",
      render: (_, record) => record.ability_name || "-",
    },
    {
      title: "备注",
      dataIndex: "note",
      key: "note",
      render: (value?: string) => value || "-",
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Space direction="vertical" size="large" style={{ width: "100%" }}>
        <Space
          align="start"
          style={{ width: "100%", justifyContent: "space-between" }}
        >
          <div>
            <Title level={3} style={{ margin: 0 }}>
              验收测评
            </Title>
          </div>
          <Space direction="vertical" size={4} style={{ minWidth: 280 }}>
            <Text>租户</Text>
            <Select
              aria-label="租户选择器"
              placeholder="选择租户"
              loading={tenantLoading}
              value={selectedAgentId}
              options={tenants.map((tenant) => ({
                label: `${tenant.tenant_id} / ${tenant.agent_id}`,
                value: tenant.agent_id,
              }))}
              onChange={handleTenantChange}
              disabled={tenants.length === 0}
            />
          </Space>
        </Space>

        <PageCompletenessPanel pageKey="evaluation" compact />

      <Alert
        type="warning"
        showIcon
        message="自动化验收阶段化开放"
        description="自动问答回放、LLM 判分、跨租户聚合和正式报告文件导出属于验收增强；当前支持租户级验收证据生成与摘要预览。"
      />

        <Row gutter={[16, 16]}>
          <Col xs={12} sm={12} lg={6}>
            <Card size="small">
              <Statistic title="测评集" value={stats.totalDatasets} />
            </Card>
          </Col>
          <Col xs={12} sm={12} lg={6}>
            <Card size="small">
              <Statistic title="题目数" value={stats.totalItems} />
            </Card>
          </Col>
          <Col xs={12} sm={12} lg={6}>
            <Card size="small">
              <Statistic title="权限边界题" value={stats.permissionBoundaryItems} />
            </Card>
          </Col>
          <Col xs={12} sm={12} lg={6}>
            <Card size="small">
              <Statistic title="Bad Case 转入" value={stats.fromBadCaseItems} />
            </Card>
          </Col>
        </Row>

        <Card>
          {tenants.length === 0 && !tenantLoading ? (
            <Text>暂无租户</Text>
          ) : (
            <Tabs
              defaultActiveKey="datasets"
              items={[
                {
                  key: "datasets",
                  label: "测评集",
                  children: (
                    <Space
                      direction="vertical"
                      size="middle"
                      style={{ width: "100%" }}
                    >
                      <Space style={{ width: "100%", justifyContent: "flex-end" }}>
                        <Button
                          onClick={() => void handleOpenBadCaseModal()}
                          loading={badCaseLoading}
                          disabled={!selectedAgentId || badCaseLoading}
                        >
                          从 Bad Case 转入
                        </Button>
                        <Button
                          type="primary"
                          loading={createLoading}
                          onClick={() => void handleCreateFromSample()}
                          disabled={!selectedAgentId || createLoading}
                        >
                          从样例创建
                        </Button>
                      </Space>
                      <Table
                        rowKey="id"
                        columns={datasetColumns}
                        dataSource={datasets}
                        loading={dataLoading}
                        pagination={false}
                      />
                    </Space>
                  ),
                },
                {
                  key: "executions",
                  label: "执行记录",
                  children: (
                    <Space
                      direction="vertical"
                      size="middle"
                      style={{ width: "100%" }}
                    >
                      <Space style={{ width: "100%", justifyContent: "space-between" }}>
                        <Text>{`已加载 ${executions.length} 条执行记录`}</Text>
                        <Button
                          type="primary"
                          onClick={handleOpenExecutionModal}
                          disabled={!selectedAgentId}
                        >
                          新建执行记录
                        </Button>
                      </Space>
                      <Table
                        rowKey="id"
                        columns={executionColumns}
                        dataSource={executions}
                        loading={dataLoading}
                        pagination={false}
                      />
                    </Space>
                  ),
                },
                {
                  key: "reports",
                  label: "准确率报告",
                  children: (
                    <Space
                      direction="vertical"
                      size="middle"
                      style={{ width: "100%" }}
                    >
                      <Space wrap>
                        <Select
                          aria-label="执行记录"
                          placeholder="选择执行记录"
                          value={selectedExecutionId}
                          style={{ minWidth: 360 }}
                          options={executions.map((item) => ({
                            label: `${item.id} / ${item.dataset_id} / ${new Date(
                              item.created_at,
                            ).toLocaleString()}`,
                            value: item.id,
                          }))}
                          onChange={handleExecutionSelectionChange}
                          disabled={!selectedAgentId || executions.length === 0}
                        />
                        <Button
                          type="primary"
                          onClick={() => void handleLoadReport()}
                          loading={reportLoading}
                          disabled={!selectedAgentId}
                        >
                          查看报告
                        </Button>
                        <Button
                          onClick={() => void handleExportEvidence()}
                          loading={evidenceLoading}
                          disabled={!selectedAgentId}
                        >
                          导出证据
                        </Button>
                      </Space>

                      {report ? (
                        <Space
                          direction="vertical"
                          size="middle"
                          style={{ width: "100%" }}
                        >
                          <Row gutter={[16, 16]}>
                            <Col xs={12} sm={8} lg={6}>
                              <Card size="small">
                                <Statistic
                                  title="正确率"
                                  value={formatAccuracyRate(report.correct_rate)}
                                />
                              </Card>
                            </Col>
                            <Col xs={12} sm={8} lg={6}>
                              <Card size="small">
                                <Statistic
                                  title="部分正确率"
                                  value={formatAccuracyRate(report.partial_rate)}
                                />
                              </Card>
                            </Col>
                            <Col xs={12} sm={8} lg={6}>
                              <Card size="small">
                                <Statistic title="总题数" value={report.total} />
                              </Card>
                            </Col>
                            <Col xs={12} sm={8} lg={6}>
                              <Card size="small">
                                <Statistic title="可执行" value={report.executable} />
                              </Card>
                            </Col>
                            <Col xs={12} sm={8} lg={6}>
                              <Card size="small">
                                <Statistic title="正确" value={report.correct} />
                              </Card>
                            </Col>
                            <Col xs={12} sm={8} lg={6}>
                              <Card size="small">
                                <Statistic title="部分正确" value={report.partial} />
                              </Card>
                            </Col>
                            <Col xs={12} sm={8} lg={6}>
                              <Card size="small">
                                <Statistic title="错误" value={report.wrong} />
                              </Card>
                            </Col>
                            <Col xs={12} sm={8} lg={6}>
                              <Card size="small">
                                <Statistic title="阻塞" value={report.blocked} />
                              </Card>
                            </Col>
                          </Row>
                          <Table
                            rowKey="key"
                            pagination={false}
                            dataSource={reportIssueRows}
                            columns={[
                              {
                                title: "问题归属",
                                dataIndex: "issue_owner",
                                key: "issue_owner",
                                render: (value: string) => getIssueOwnerLabel(value),
                              },
                              {
                                title: "数量",
                                dataIndex: "count",
                                key: "count",
                              },
                            ]}
                          />
                          {evidence ? (
                            <Card size="small" title="验收证据">
                              <Space direction="vertical" size={4}>
                                <Text>{`版本：${evidence.evidence_version}`}</Text>
                                <Text>{`租户：${evidence.tenant_id} / ${evidence.agent_id}`}</Text>
                                <Text>{`测评集：${evidence.dataset.name} / ${evidence.dataset.id}`}</Text>
                                <Text>{`执行：${evidence.execution.id}`}</Text>
                                <Text>{`导出时间：${formatDateTime(evidence.exported_at)}`}</Text>
                              </Space>
                            </Card>
                          ) : null}
                        </Space>
                      ) : (
                        <Space
                          direction="vertical"
                          size="middle"
                          style={{ width: "100%" }}
                        >
                          <Empty description="请选择执行记录并查看报告" />
                          {evidence ? (
                            <Card size="small" title="验收证据">
                              <Space direction="vertical" size={4}>
                                <Text>{`版本：${evidence.evidence_version}`}</Text>
                                <Text>{`租户：${evidence.tenant_id} / ${evidence.agent_id}`}</Text>
                                <Text>{`测评集：${evidence.dataset.name} / ${evidence.dataset.id}`}</Text>
                                <Text>{`执行：${evidence.execution.id}`}</Text>
                                <Text>{`导出时间：${formatDateTime(evidence.exported_at)}`}</Text>
                              </Space>
                            </Card>
                          ) : null}
                        </Space>
                      )}
                    </Space>
                  ),
                },
              ]}
            />
          )}
        </Card>
      </Space>

      <Modal
        title="从 Bad Case 转入测评集"
        open={badCaseModalOpen}
        onCancel={handleCloseBadCaseModal}
        footer={null}
        destroyOnHidden
        getContainer={false}
      >
        <Space direction="vertical" size="middle" style={{ width: "100%" }}>
          <Table
            rowKey="case_id"
            columns={badCaseColumns}
            dataSource={badCases}
            pagination={false}
            rowSelection={{
              selectedRowKeys: selectedBadCaseIds,
              onChange: (nextSelectedRowKeys) => {
                setSelectedBadCaseIds(nextSelectedRowKeys)
              },
              getCheckboxProps: (record) =>
                ({
                  "aria-label": `选择 ${record.case_id}`,
                }) as Partial<Omit<CheckboxProps, "defaultChecked" | "checked">>,
            }}
          />

          <Form form={badCaseForm} layout="vertical">
            <Form.Item label="目标测评集" name="dataset_id">
              <Select
                aria-label="目标测评集"
                placeholder="选择已有测评集"
                allowClear
                options={datasets.map((item) => ({
                  label: item.name,
                  value: item.id,
                }))}
              />
            </Form.Item>
            <Form.Item label="新测评集名称" name="dataset_name">
              <Input
                aria-label="新测评集名称"
                placeholder="未选择目标测评集时必填"
                disabled={Boolean(selectedBadCaseDatasetId)}
              />
            </Form.Item>

            <Space style={{ width: "100%", justifyContent: "flex-end" }}>
              <Button onClick={handleCloseBadCaseModal}>取消</Button>
              <Button
                type="primary"
                loading={badCaseSubmitting}
                onClick={() => void handleSubmitBadCases()}
              >
                转入测评集
              </Button>
            </Space>
          </Form>
        </Space>
      </Modal>

      <Modal
        title="新建执行记录"
        open={executionModalOpen}
        onCancel={handleCloseExecutionModal}
        footer={null}
        destroyOnHidden
        getContainer={false}
      >
        <Form form={executionForm} layout="vertical">
          <Form.Item
            label="测评集"
            name="dataset_id"
            rules={[{ required: true, message: "请选择测评集" }]}
          >
            <Select
              aria-label="测评集"
              placeholder="选择测评集"
              options={datasets.map((item) => ({
                label: item.name,
                value: item.id,
              }))}
              onChange={() => executionForm.setFieldValue("cases", undefined)}
            />
          </Form.Item>

          {selectedDataset ? (
            <Space direction="vertical" size="middle" style={{ width: "100%" }}>
              {selectedDataset.items.map((item) => (
                <Card key={item.case_id} size="small" title={item.case_id}>
                  <Space direction="vertical" size="small" style={{ width: "100%" }}>
                    <Text>{item.question}</Text>
                    <Form.Item
                      label={`${item.case_id} 实际回答`}
                      name={["cases", item.case_id, "actual"]}
                    >
                      <TextArea
                        aria-label={`${item.case_id} 实际回答`}
                        rows={3}
                      />
                    </Form.Item>
                    <Form.Item
                      label={`${item.case_id} 结果`}
                      name={["cases", item.case_id, "result"]}
                    >
                      <Select
                        aria-label={`${item.case_id} 结果`}
                        placeholder="选择结果"
                        options={EVAL_RESULT_OPTIONS}
                      />
                    </Form.Item>
                    <Form.Item
                      label={`${item.case_id} 问题归属`}
                      name={["cases", item.case_id, "issue_owner"]}
                    >
                      <Select
                        aria-label={`${item.case_id} 问题归属`}
                        placeholder="选择问题归属"
                        options={EVAL_ISSUE_OWNER_OPTIONS}
                        allowClear
                      />
                    </Form.Item>
                    <Form.Item
                      label={`${item.case_id} 处理动作`}
                      name={["cases", item.case_id, "action"]}
                    >
                      <Select
                        aria-label={`${item.case_id} 处理动作`}
                        placeholder="选择处理动作"
                        options={EVAL_ACTION_OPTIONS}
                        allowClear
                      />
                    </Form.Item>
                    <Form.Item
                      label={`${item.case_id} Trace ID`}
                      name={["cases", item.case_id, "trace_id"]}
                    >
                      <Input aria-label={`${item.case_id} Trace ID`} />
                    </Form.Item>
                    <Form.Item
                      label={`${item.case_id} Request ID`}
                      name={["cases", item.case_id, "request_id"]}
                    >
                      <Input aria-label={`${item.case_id} Request ID`} />
                    </Form.Item>
                    <Form.Item
                      label={`${item.case_id} 备注`}
                      name={["cases", item.case_id, "note"]}
                    >
                      <TextArea aria-label={`${item.case_id} 备注`} rows={2} />
                    </Form.Item>
                  </Space>
                </Card>
              ))}
              <Space style={{ width: "100%", justifyContent: "flex-end" }}>
                <Button onClick={handleCloseExecutionModal}>取消</Button>
                <Button
                  type="primary"
                  loading={executionSaving}
                  onClick={() => void handleSubmitExecution()}
                >
                  提交执行记录
                </Button>
              </Space>
            </Space>
          ) : (
            <Empty description="请选择测评集后填写执行结果" />
          )}
        </Form>
      </Modal>

      <Drawer
        title="测评题目"
        open={drawerOpen}
        onClose={handleCloseDrawer}
        width={900}
        getContainer={false}
      >
        <Space direction="vertical" size="middle" style={{ width: "100%" }}>
          <Text>{activeDataset ? activeDataset.name : "-"}</Text>
          <Table
            rowKey="case_id"
            columns={itemColumns}
            dataSource={activeDataset?.items ?? []}
            pagination={false}
          />
        </Space>
      </Drawer>
    </div>
  )
}

export default EvaluationPage
