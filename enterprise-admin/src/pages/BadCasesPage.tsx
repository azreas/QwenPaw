import React, { useCallback, useEffect, useMemo, useState } from "react"
import {
  Alert,
  Button,
  Card,
  Col,
  Drawer,
  Form,
  Input,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
  message,
} from "antd"
import type { ColumnsType } from "antd/es/table"
import { ApiError } from "@/api/http"
import {
  listTenantBadCases,
  updateTenantBadCase,
} from "@/api/ops"
import { listWecomTenants } from "@/api/tenants"
import type {
  BadCaseCategory,
  BadCaseItem,
  BadCaseStatus,
  WecomTenantSummary,
} from "@/api/types"
import {
  BAD_CASE_CATEGORY_OPTIONS,
  BAD_CASE_STATUS_OPTIONS,
  buildBadCaseStats,
  getBadCaseCategoryLabel,
  getBadCaseStatusTag,
} from "@/features/ops/badCaseModel"
import { formatTraceCallName, formatTraceCallType } from "@/features/ops/traceModel"
import PageCompletenessPanel from "@/features/platform-readiness/PageCompletenessPanel"

const { Title, Text } = Typography
const { TextArea } = Input

const BAD_CASE_STATUS_VALUES = new Set<string>(
  BAD_CASE_STATUS_OPTIONS.map((item) => item.value),
)
const BAD_CASE_CATEGORY_VALUES = new Set<string>(
  BAD_CASE_CATEGORY_OPTIONS.map((item) => item.value),
)

interface EditBadCaseFormValues {
  status: BadCaseStatus
  category: BadCaseCategory
  owner?: string
  note?: string
}

function getBadCaseErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiError && err.isForbidden()) {
    return "当前身份无权查看或更新 Bad Case"
  }
  if (err instanceof ApiError && err.status === 503) {
    return "审计服务不可用，Bad Case 未保存"
  }
  return err instanceof Error ? err.message : fallback
}

function formatDateTime(value?: string | null): string {
  if (!value) {
    return "-"
  }
  return new Date(value).toLocaleString()
}

function normalizeBadCaseStatus(status: string): BadCaseStatus {
  return BAD_CASE_STATUS_VALUES.has(status) ? (status as BadCaseStatus) : "open"
}

function normalizeBadCaseCategory(category: string): BadCaseCategory {
  return BAD_CASE_CATEGORY_VALUES.has(category)
    ? (category as BadCaseCategory)
    : "platform_runtime"
}

const BadCasesPage: React.FC = () => {
  const [form] = Form.useForm<EditBadCaseFormValues>()
  const [tenants, setTenants] = useState<WecomTenantSummary[]>([])
  const [selectedAgentId, setSelectedAgentId] = useState<string>()
  const [badCases, setBadCases] = useState<BadCaseItem[]>([])
  const [tenantLoading, setTenantLoading] = useState(true)
  const [caseLoading, setCaseLoading] = useState(false)
  const [saveLoading, setSaveLoading] = useState(false)
  const [statusFilter, setStatusFilter] = useState<BadCaseStatus | undefined>()
  const [categoryFilter, setCategoryFilter] = useState<
    BadCaseCategory | undefined
  >()
  const [editingCase, setEditingCase] = useState<BadCaseItem | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)

  const loadBadCases = useCallback(async (agentId: string) => {
    try {
      setCaseLoading(true)
      const response = await listTenantBadCases(agentId)
      setBadCases(response.items)
    } catch (err) {
      setBadCases([])
      message.error(getBadCaseErrorMessage(err, "加载 Bad Case 失败"))
    } finally {
      setCaseLoading(false)
    }
  }, [])

  const loadTenants = useCallback(async () => {
    try {
      setTenantLoading(true)
      const response = await listWecomTenants()
      const nextTenants = response.tenants
      setTenants(nextTenants)
      if (nextTenants.length === 0) {
        setSelectedAgentId(undefined)
        setBadCases([])
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
      setSelectedAgentId(undefined)
      setBadCases([])
      message.error(getBadCaseErrorMessage(err, "加载租户列表失败"))
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
    void loadBadCases(selectedAgentId)
  }, [loadBadCases, selectedAgentId])

  const stats = useMemo(() => buildBadCaseStats(badCases), [badCases])

  const filteredBadCases = useMemo(
    () =>
      badCases.filter((item) => {
        if (statusFilter && item.status !== statusFilter) {
          return false
        }
        if (categoryFilter && item.category !== categoryFilter) {
          return false
        }
        return true
      }),
    [badCases, categoryFilter, statusFilter],
  )

  const openDrawer = (record: BadCaseItem) => {
    setEditingCase(record)
    setDrawerOpen(true)
    form.setFieldsValue({
      status: normalizeBadCaseStatus(record.status),
      category: normalizeBadCaseCategory(record.category),
      owner: record.owner,
      note: record.note,
    })
  }

  const closeDrawer = () => {
    setDrawerOpen(false)
    setEditingCase(null)
    form.resetFields()
  }

  const handleSave = async (values: EditBadCaseFormValues) => {
    if (!selectedAgentId || !editingCase) return
    try {
      setSaveLoading(true)
      await updateTenantBadCase(selectedAgentId, editingCase.case_id, {
        status: values.status,
        category: values.category,
        owner: values.owner?.trim() || "",
        note: values.note?.trim() || "",
      })
      message.success("Bad Case 已更新")
      setDrawerOpen(false)
      setEditingCase(null)
      await loadBadCases(selectedAgentId)
    } catch (err) {
      message.error(getBadCaseErrorMessage(err, "更新 Bad Case 失败"))
    } finally {
      setSaveLoading(false)
    }
  }

  const columns: ColumnsType<BadCaseItem> = [
    {
      title: "Case ID",
      dataIndex: "case_id",
      key: "case_id",
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      render: (value: BadCaseStatus) => {
        const tag = getBadCaseStatusTag(value)
        return <Tag color={tag.color}>{tag.text}</Tag>
      },
    },
    {
      title: "分类",
      dataIndex: "category",
      key: "category",
      render: (value: BadCaseCategory) => getBadCaseCategoryLabel(value),
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
      title: "入口",
      dataIndex: "entrypoint",
      key: "entrypoint",
    },
    {
      title: "负责人",
      dataIndex: "owner",
      key: "owner",
      render: (value?: string | null) => value || "-",
    },
    {
      title: "备注",
      dataIndex: "note",
      key: "note",
      render: (value?: string | null) => value || "-",
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
          aria-label={`编辑 ${record.case_id}`}
          onClick={() => openDrawer(record)}
        >
          编辑
        </Button>
      ),
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
              Bad Case
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
              onChange={setSelectedAgentId}
              disabled={tenants.length === 0}
            />
          </Space>
        </Space>

        <PageCompletenessPanel pageKey="badCases" compact />

        <Alert
          type="info"
          showIcon
          message="问题治理阶段化开放"
          description="证据详情、SLA、批量分派、导出和验收联动将按租户边界逐步开放；当前页面已支持状态、分类、负责人和备注流转。"
        />

        <Row gutter={[16, 16]}>
          <Col xs={12} sm={8} lg={4}>
            <Card size="small">
              <Statistic title="总数" value={stats.total} />
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={4}>
            <Card size="small">
              <Statistic title="待处理" value={stats.open} />
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={4}>
            <Card size="small">
              <Statistic title="已分诊" value={stats.triaged} />
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={4}>
            <Card size="small">
              <Statistic title="已转交" value={stats.transferred} />
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={4}>
            <Card size="small">
              <Statistic title="已解决" value={stats.resolved} />
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={4}>
            <Card size="small">
              <Statistic title="已忽略" value={stats.ignored} />
            </Card>
          </Col>
        </Row>

        <Card>
          {tenants.length === 0 && !tenantLoading ? (
            <Text>暂无租户</Text>
          ) : (
            <Space direction="vertical" size="large" style={{ width: "100%" }}>
              <Row gutter={[16, 0]}>
                <Col xs={24} sm={12} lg={6}>
                  <Space direction="vertical" size={4} style={{ width: "100%" }}>
                    <Text>状态</Text>
                    <Select
                      aria-label="状态"
                      allowClear
                      style={{ width: "100%" }}
                      value={statusFilter}
                      options={BAD_CASE_STATUS_OPTIONS}
                      onChange={setStatusFilter}
                    />
                  </Space>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                  <Space direction="vertical" size={4} style={{ width: "100%" }}>
                    <Text>分类</Text>
                    <Select
                      aria-label="分类"
                      allowClear
                      style={{ width: "100%" }}
                      value={categoryFilter}
                      options={BAD_CASE_CATEGORY_OPTIONS}
                      onChange={setCategoryFilter}
                    />
                  </Space>
                </Col>
              </Row>

              <Table
                rowKey="case_id"
                columns={columns}
                dataSource={filteredBadCases}
                loading={caseLoading}
                pagination={false}
              />
            </Space>
          )}
        </Card>
      </Space>

      <Drawer
        title="编辑 Bad Case"
        open={drawerOpen}
        onClose={closeDrawer}
        width={480}
        extra={
          <Space>
            <Button onClick={closeDrawer}>取消</Button>
            <Button
              type="primary"
              loading={saveLoading}
              onClick={() => form.submit()}
            >
              保存
            </Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical" onFinish={handleSave}>
          <Form.Item label="状态" name="status" rules={[{ required: true }]}>
            <Select options={BAD_CASE_STATUS_OPTIONS} />
          </Form.Item>
          <Form.Item label="分类" name="category" rules={[{ required: true }]}>
            <Select options={BAD_CASE_CATEGORY_OPTIONS} />
          </Form.Item>
          <Form.Item label="负责人" name="owner">
            <Input />
          </Form.Item>
          <Form.Item label="备注" name="note">
            <TextArea rows={4} />
          </Form.Item>
        </Form>
      </Drawer>
    </div>
  )
}

export default BadCasesPage
