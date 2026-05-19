import React, { useCallback, useEffect, useMemo, useState } from "react"
import {
  Alert,
  Button,
  Card,
  Col,
  Form,
  Input,
  Modal,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Tabs,
  Typography,
  message,
} from "antd"
import type { ColumnsType } from "antd/es/table"
import { listBusinessCalls } from "@/api/audit"
import type { BusinessCallItem, BusinessCallQuery } from "@/api/audit"
import { ApiError } from "@/api/http"
import {
  getOpsOverview,
  getTenantOpsSummary,
  markTenantBadCase,
} from "@/api/ops"
import { listWecomTenants } from "@/api/tenants"
import type {
  BadCaseCategory,
  OpsOverviewResponse,
  TenantOpsSummaryResponse,
  WecomTenantSummary,
} from "@/api/types"
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
  TRACE_STATUS_OPTIONS,
} from "@/features/ops/traceModel"

import {
  BAD_CASE_CATEGORY_OPTIONS,
} from "@/features/ops/badCaseModel"
import PageCompletenessPanel from "@/features/platform-readiness/PageCompletenessPanel"

const { Title, Text } = Typography

interface TraceFilterFormValues {
  call_type?: string
  call_name?: string
  entrypoint?: string
  status?: string
  error_code?: string
  error_reason?: string
  request_id?: string
  trace_id?: string
}

interface MarkBadCaseFormValues {
  category: BadCaseCategory
  owner?: string
  note?: string
}

function getTraceErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiError && err.isForbidden()) {
    return "当前身份无权查看业务追踪或未绑定租户"
  }
  return err instanceof Error ? err.message : fallback
}

function getMarkBadCaseErrorMessage(err: unknown): string {
  if (err instanceof ApiError && err.status === 409) {
    return "该调用已标记为 Bad Case"
  }
  if (err instanceof ApiError && err.status === 503) {
    return "审计服务不可用，Bad Case 未保存"
  }
  if (err instanceof ApiError && err.isForbidden()) {
    return "当前身份无权标记 Bad Case"
  }
  return err instanceof Error ? err.message : "标记 Bad Case 失败"
}

function formatDateTime(value?: string | null): string {
  if (!value) {
    return "-"
  }
  return new Date(value).toLocaleString()
}

function formatDuration(value?: number | null): string {
  return typeof value === "number" ? `${value} ms` : "-"
}

const BusinessTracePage: React.FC = () => {
  const [form] = Form.useForm<TraceFilterFormValues>()
  const [markForm] = Form.useForm<MarkBadCaseFormValues>()
  const [tenants, setTenants] = useState<WecomTenantSummary[]>([])
  const [selectedAgentId, setSelectedAgentId] = useState<string>()
  const [overview, setOverview] = useState<OpsOverviewResponse | null>(null)
  const [summary, setSummary] = useState<TenantOpsSummaryResponse | null>(null)
  const [traces, setTraces] = useState<BusinessCallItem[]>([])
  const [tenantLoading, setTenantLoading] = useState(true)
  const [overviewLoading, setOverviewLoading] = useState(true)
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [traceLoading, setTraceLoading] = useState(false)
  const [markingTrace, setMarkingTrace] = useState<BusinessCallItem | null>(null)
  const [markLoading, setMarkLoading] = useState(false)

  const loadOverview = useCallback(async () => {
    try {
      setOverviewLoading(true)
      const response = await getOpsOverview()
      setOverview(response)
    } catch (err) {
      setOverview(null)
      message.error(getTraceErrorMessage(err, "加载业务追踪概览失败"))
    } finally {
      setOverviewLoading(false)
    }
  }, [])

  const loadTenants = useCallback(async () => {
    try {
      setTenantLoading(true)
      const response = await listWecomTenants()
      setTenants(response.tenants)
      if (response.tenants.length === 0) {
        setSelectedAgentId(undefined)
        setSummary(null)
        setTraces([])
        return
      }
      setSelectedAgentId((current) => {
        if (
          current &&
          response.tenants.some((tenant) => tenant.agent_id === current)
        ) {
          return current
        }
        return response.tenants[0].agent_id
      })
    } catch (err) {
      setTenants([])
      setSelectedAgentId(undefined)
      setSummary(null)
      setTraces([])
      message.error(getTraceErrorMessage(err, "加载租户列表失败"))
    } finally {
      setTenantLoading(false)
    }
  }, [])

  const loadTenantData = useCallback(
    async (agentId: string, query: BusinessCallQuery) => {
      try {
        setSummaryLoading(true)
        setTraceLoading(true)
        const [summaryResponse, traceResponse] = await Promise.all([
          getTenantOpsSummary(agentId),
          listBusinessCalls({ ...query, agent_id: agentId }),
        ])
        setSummary(summaryResponse)
        setTraces(traceResponse.items)
      } catch (err) {
        setSummary(null)
        setTraces([])
        message.error(getTraceErrorMessage(err, "加载业务追踪失败"))
      } finally {
        setSummaryLoading(false)
        setTraceLoading(false)
      }
    },
    [],
  )

  useEffect(() => {
    void loadOverview()
    void loadTenants()
  }, [loadOverview, loadTenants])

  useEffect(() => {
    if (!selectedAgentId) {
      return
    }
    void loadTenantData(selectedAgentId, buildTraceFilters({}))
  }, [loadTenantData, selectedAgentId])

  const traceStats = useMemo(
    () => summarizeTraceStats(summary, traces),
    [summary, traces],
  )

  const handleQuery = async () => {
    if (!selectedAgentId) {
      return
    }
    const values = form.getFieldsValue()
    const query = buildTraceFilters(values)
    await loadTenantData(selectedAgentId, query)
  }

  const handleMarkBadCase = async (values: MarkBadCaseFormValues) => {
    if (!selectedAgentId || !markingTrace) {
      return
    }
    try {
      setMarkLoading(true)
      await markTenantBadCase(selectedAgentId, {
        source_audit_id: markingTrace.id,
        source_request_id: markingTrace.request_id || "",
        source_trace_id: markingTrace.trace_id || "",
        category: values.category,
        owner: values.owner?.trim() || "",
        note: values.note?.trim() || "",
      })
      message.success("Bad Case 已标记")
      setMarkingTrace(null)
      markForm.resetFields()
    } catch (err) {
      message.error(getMarkBadCaseErrorMessage(err))
    } finally {
      setMarkLoading(false)
    }
  }

  const traceColumns: ColumnsType<BusinessCallItem> = [
    {
      title: "时间",
      dataIndex: "created_at",
      key: "created_at",
      render: (value: string) => formatDateTime(value),
    },
    {
      title: "入口",
      dataIndex: "entrypoint",
      key: "entrypoint",
      render: (value?: string | null) => value || "-",
    },
    {
      title: "调用类型",
      key: "call_type",
      render: (_, record) => formatTraceCallType(record),
    },
    {
      title: "调用名称",
      key: "call_name",
      render: (_, record) => formatTraceCallName(record),
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      render: (value: string) => {
        const tag = getTraceStatusTag(value)
        return <Tag color={tag.color}>{tag.text}</Tag>
      },
    },
    {
      title: "耗时",
      dataIndex: "duration_ms",
      key: "duration_ms",
      render: (value: number) => formatDuration(value),
    },
    {
      title: "错误原因",
      dataIndex: "error_reason",
      key: "error_reason",
      render: (value?: string | null) => value || "-",
    },
    {
      title: "错误码",
      dataIndex: "error_code",
      key: "error_code",
      render: (value?: string | null) => value || "-",
    },
    {
      title: "Request ID",
      dataIndex: "request_id",
      key: "request_id",
      render: (value?: string | null) => value || "-",
    },
    {
      title: "Trace ID",
      dataIndex: "trace_id",
      key: "trace_id",
      render: (value?: string | null) => value || "-",
    },
    {
      title: "操作",
      key: "action",
      render: (_, record) => {
        if (isTraceSuccessful(record.status)) {
          return "-"
        }
        return (
          <Button
            type="link"
            size="small"
            aria-label={`标记 ${record.id}`}
            onClick={() => {
              setMarkingTrace(record)
              markForm.setFieldsValue({
                category: "platform_runtime",
                owner: "",
                note: record.error_reason || "",
              })
            }}
          >
            标记 Bad Case
          </Button>
        )
      },
    },
  ]

  const healthTag = getHealthStatusTag(summary?.health_status ?? "unknown")

  const businessTraceContent =
    tenants.length === 0 && !tenantLoading ? (
      <Text>暂无租户</Text>
    ) : (
      <Space direction="vertical" size="large" style={{ width: "100%" }}>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleQuery}
        >
          <Row gutter={[16, 0]}>
            <Col xs={24} sm={12} lg={4}>
              <Form.Item label="调用类型" name="call_type">
                <Select
                  allowClear
                  options={TRACE_CALL_TYPE_OPTIONS}
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} lg={4}>
              <Form.Item label="调用名称" name="call_name">
                <Input />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} lg={4}>
              <Form.Item label="入口" name="entrypoint">
                <Input />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} lg={4}>
              <Form.Item label="状态" name="status">
                <Select allowClear options={TRACE_STATUS_OPTIONS} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} lg={4}>
              <Form.Item label="错误码" name="error_code">
                <Input />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} lg={4}>
              <Form.Item label="错误原因" name="error_reason">
                <Input />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} lg={4}>
              <Form.Item label="Request ID" name="request_id">
                <Input />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} lg={4}>
              <Form.Item label="Trace ID" name="trace_id">
                <Input />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} lg={4}>
              <Form.Item label=" ">
                <Button type="primary" htmlType="submit">
                  查询
                </Button>
              </Form.Item>
            </Col>
          </Row>
        </Form>

        <Table
          rowKey="id"
          columns={traceColumns}
          dataSource={traces}
          loading={traceLoading}
          pagination={false}
        />
      </Space>
    )

  return (
    <div style={{ padding: 24 }}>
      <Space direction="vertical" size="large" style={{ width: "100%" }}>
        <Space
          align="start"
          style={{ width: "100%", justifyContent: "space-between" }}
        >
          <div>
            <Title level={3} style={{ margin: 0 }}>
              业务追踪
            </Title>
          </div>
          <Space direction="vertical" size={4} style={{ minWidth: 280 }}>
            <Text>租户</Text>
            <Select
              placeholder="选择租户"
              loading={tenantLoading}
              value={selectedAgentId}
              options={tenants.map((tenant) => ({
                label: `${tenant.tenant_id} / ${tenant.agent_id}`,
                value: tenant.agent_id,
              }))}
              onChange={setSelectedAgentId}
              disabled={tenants.length === 0}
            />
          </Space>
        </Space>

        <PageCompletenessPanel pageKey="audit" compact />

        <Row gutter={[16, 16]}>
          <Col xs={12} sm={8} lg={4}>
            <Card size="small" loading={overviewLoading}>
              <Statistic title="租户总数" value={overview?.total_tenants ?? 0} />
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={4}>
            <Card size="small" loading={overviewLoading}>
              <Statistic title="运行中租户" value={overview?.running_tenants ?? 0} />
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={4}>
            <Card size="small" loading={overviewLoading}>
              <Statistic title="24h 调用" value={overview?.business_calls_24h ?? 0} />
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={4}>
            <Card size="small" loading={overviewLoading}>
              <Statistic title="24h 失败" value={overview?.failed_calls_24h ?? 0} />
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={4}>
            <Card size="small" loading={overviewLoading}>
              <Statistic
                title="失败率"
                value={formatFailureRate(overview?.failure_rate ?? 0)}
              />
            </Card>
          </Col>
        </Row>

        <Row gutter={[16, 16]}>
          <Col xs={12} sm={8} lg={6}>
            <Card size="small" loading={summaryLoading}>
              <Statistic
                title="租户健康"
                value={healthTag.text}
                valueStyle={{
                  color: healthTag.color === "green" ? "#389e0d" : undefined,
                }}
              />
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={6}>
            <Card size="small" loading={summaryLoading}>
              <Statistic title="可见调用" value={traceStats.visibleTotal} />
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={6}>
            <Card size="small" loading={summaryLoading}>
              <Statistic title="可见失败" value={traceStats.visibleFailures} />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card size="small" loading={summaryLoading}>
              <Statistic
                title="最近活动"
                value={formatDateTime(summary?.last_activity_at)}
                valueStyle={{ fontSize: 14 }}
              />
            </Card>
          </Col>
        </Row>

        <Card>
          <Tabs
            defaultActiveKey="business-trace"
            items={[
              {
                key: "business-trace",
                label: "业务调用",
                children: businessTraceContent,
              },
              {
                key: "audit-log",
                label: "审计日志",
                children: (
                  <Alert
                    type="info"
                    showIcon
                    message="审计日志阶段建设中"
                    description="当前阶段仅提供只读说明；后续将补齐通用审计日志搜索、权限拒绝事件、导出和保存筛选。"
                  />
                ),
              },
            ]}
          />
        </Card>
      </Space>
      <Modal
        title="标记 Bad Case"
        open={Boolean(markingTrace)}
        onCancel={() => {
          setMarkingTrace(null)
          markForm.resetFields()
        }}
        onOk={() => markForm.submit()}
        okText="确认标记"
        cancelText="取消"
        confirmLoading={markLoading}
      >
        <Form
          form={markForm}
          layout="vertical"
          initialValues={{ category: "platform_runtime" }}
          onFinish={handleMarkBadCase}
        >
          <Form.Item label="分类" name="category" rules={[{ required: true }]}>
            <Select options={BAD_CASE_CATEGORY_OPTIONS} />
          </Form.Item>
          <Form.Item label="负责人" name="owner">
            <Input />
          </Form.Item>
          <Form.Item label="备注" name="note">
            <Input.TextArea rows={4} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default BusinessTracePage
