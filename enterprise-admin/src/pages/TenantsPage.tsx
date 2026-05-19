import React, { useCallback, useEffect, useState } from "react"
import {
  Card,
  Table,
  Button,
  Modal,
  Drawer,
  Tag,
  Statistic,
  Row,
  Col,
  Switch,
  Input,
  Form,
  message,
  Spin,
  Space,
  Typography,
  Descriptions,
  Tabs,
  Alert,
  List,
  Select,
} from "antd"
import {
  PlusOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  ReloadOutlined,
  InfoCircleOutlined,
} from "@ant-design/icons"
import type { ColumnsType } from "antd/es/table"
import type { WecomTenantSummary } from "@/api/types"
import {
  listWecomTenants,
  createWecomTenant,
  startWecomTenant,
  stopWecomTenant,
  restartWecomTenant,
} from "@/api/tenants"
import {
  getTenantHealth,
  listTenantCronJobs,
  listTenantMemoryFiles,
  listTenantWorkspaceFiles,
  pauseTenantCronJob,
  resumeTenantCronJob,
  runTenantCronJob,
} from "@/api/tenantRuntime"
import {
  listTenantMcpClients,
  listTenantSkills,
  listTenantTools,
} from "@/api/abilities"
import { getTenantLlmRouting, getTenantModel } from "@/api/models"
import { diagnoseTenantEntryConfig } from "@/api/entryConfig"
import {
  getTenantSecuritySettings,
  getTenantSystemPrompts,
  listTenantTemplates,
  putTenantSecuritySettings,
  putTenantSystemPrompts,
} from "@/api/agentConfig"
import type {
  AgentsLLMRoutingConfig,
  MCPClientInfo,
  ModelSlotConfig,
  SkillInfo,
  SystemPromptFilesResponse,
  TenantCronJob,
  TenantEntryDiagnostics,
  TenantHealthResponse,
  TenantRuntimeFileInfo,
  TenantSecuritySettings,
  TenantTemplate,
  ToolInfo,
} from "@/api/types"
import {
  buildTenantStats,
  getTenantDisplayStatus,
  sortTenantsForTable,
} from "@/features/tenants/tenantModel"
import type { TenantStats } from "@/features/tenants/tenantModel"
import PageCompletenessPanel from "@/features/platform-readiness/PageCompletenessPanel"

const { Title } = Typography

/** 新建租户表单值 */
interface CreateFormValues {
  tenant_id: string
  startAfterCreate: boolean
}

interface RuntimeSnapshot {
  health: TenantHealthResponse | null
  files: TenantRuntimeFileInfo[]
  memoryFiles: TenantRuntimeFileInfo[]
  cronJobs: TenantCronJob[]
  skills: SkillInfo[]
  tools: ToolInfo[]
  mcpClients: MCPClientInfo[]
  model: ModelSlotConfig | null
  routing: AgentsLLMRoutingConfig | null
  entryDiagnostics: TenantEntryDiagnostics | null
  templates: TenantTemplate[]
  systemPrompts: SystemPromptFilesResponse | null
  security: TenantSecuritySettings | null
}

const TenantsPage: React.FC = () => {
  const [tenants, setTenants] = useState<WecomTenantSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState<TenantStats>({
    total: 0,
    running: 0,
    initialized: 0,
    runtimeOnly: 0,
    totalChats: 0,
    totalJobs: 0,
  })
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [createLoading, setCreateLoading] = useState(false)
  const [detailDrawerOpen, setDetailDrawerOpen] = useState(false)
  const [detailTenant, setDetailTenant] = useState<WecomTenantSummary | null>(
    null,
  )
  const [runtimeSnapshot, setRuntimeSnapshot] = useState<RuntimeSnapshot>({
    health: null,
    files: [],
    memoryFiles: [],
    cronJobs: [],
    skills: [],
    tools: [],
    mcpClients: [],
    model: null,
    routing: null,
    entryDiagnostics: null,
    templates: [],
    systemPrompts: null,
    security: null,
  })
  const [runtimeLoading, setRuntimeLoading] = useState(false)
  const [runtimeError, setRuntimeError] = useState("")
  const [cronActionLoading, setCronActionLoading] = useState<Record<string, boolean>>(
    {},
  )
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>(
    {},
  )
  const [form] = Form.useForm<CreateFormValues>()

  /** 加载租户列表 */
  const loadTenants = useCallback(async () => {
    try {
      setLoading(true)
      const resp = await listWecomTenants()
      const sorted = sortTenantsForTable(resp.tenants)
      setTenants(sorted)
      setStats(buildTenantStats(resp.tenants))
    } catch (err) {
      message.error(
        err instanceof Error ? err.message : "加载租户列表失败",
      )
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadTenants()
  }, [loadTenants])

  /** 新建租户 */
  const handleCreate = async (values: CreateFormValues) => {
    try {
      setCreateLoading(true)
      await createWecomTenant({
        tenant_id: values.tenant_id,
        start: values.startAfterCreate,
      })
      message.success("租户创建成功")
      setCreateModalOpen(false)
      form.resetFields()
      await loadTenants()
    } catch (err) {
      message.error(
        err instanceof Error ? err.message : "创建租户失败",
      )
    } finally {
      setCreateLoading(false)
    }
  }

  /** 执行租户操作（启动/停止/重启） */
  const handleAction = async (
    agentId: string,
    action: "start" | "stop" | "restart",
  ) => {
    const actionFn = { start: startWecomTenant, stop: stopWecomTenant, restart: restartWecomTenant }[action]
    const actionLabel = { start: "启动", stop: "停止", restart: "重启" }[action]
    try {
      setActionLoading((prev) => ({ ...prev, [agentId]: true }))
      await actionFn(agentId)
      message.success(`${actionLabel}成功`)
      await loadTenants()
    } catch (err) {
      message.error(
        err instanceof Error ? err.message : `${actionLabel}失败`,
      )
    } finally {
      setActionLoading((prev) => ({ ...prev, [agentId]: false }))
    }
  }

  /** 查看租户详情 */
  const handleDetail = (tenant: WecomTenantSummary) => {
    setDetailTenant(tenant)
    setDetailDrawerOpen(true)
  }

  const loadRuntimeSnapshot = useCallback(async (agentId: string) => {
    try {
      setRuntimeLoading(true)
      setRuntimeError("")
      const [
        health,
        files,
        memory,
        cronJobs,
        skills,
        tools,
        mcpClients,
        model,
        routing,
        entryDiagnostics,
        templates,
        systemPrompts,
        security,
      ] = await Promise.all([
        getTenantHealth(agentId),
        listTenantWorkspaceFiles(agentId),
        listTenantMemoryFiles(agentId),
        listTenantCronJobs(agentId),
        listTenantSkills(agentId),
        listTenantTools(agentId),
        listTenantMcpClients(agentId),
        getTenantModel(agentId),
        getTenantLlmRouting(agentId),
        diagnoseTenantEntryConfig(agentId),
        listTenantTemplates(),
        getTenantSystemPrompts(agentId),
        getTenantSecuritySettings(agentId),
      ])
      setRuntimeSnapshot({
        health,
        files: files.files,
        memoryFiles: memory.files,
        cronJobs,
        skills,
        tools,
        mcpClients,
        model,
        routing,
        entryDiagnostics,
        templates: templates.templates,
        systemPrompts,
        security,
      })
    } catch (err) {
      setRuntimeError(
        err instanceof Error ? err.message : "加载租户运行资源失败",
      )
      setRuntimeSnapshot({
        health: null,
        files: [],
        memoryFiles: [],
        cronJobs: [],
        skills: [],
        tools: [],
        mcpClients: [],
        model: null,
        routing: null,
        entryDiagnostics: null,
        templates: [],
        systemPrompts: null,
        security: null,
      })
    } finally {
      setRuntimeLoading(false)
    }
  }, [])

  useEffect(() => {
    if (detailDrawerOpen && detailTenant) {
      loadRuntimeSnapshot(detailTenant.agent_id)
    }
  }, [detailDrawerOpen, detailTenant, loadRuntimeSnapshot])

  const handleCronAction = async (
    jobId: string,
    action: "pause" | "resume" | "run",
  ) => {
    if (!detailTenant) return
    const actionFn = {
      pause: pauseTenantCronJob,
      resume: resumeTenantCronJob,
      run: runTenantCronJob,
    }[action]
    const label = { pause: "暂停", resume: "恢复", run: "运行" }[action]
    try {
      setCronActionLoading((prev) => ({ ...prev, [jobId]: true }))
      await actionFn(detailTenant.agent_id, jobId)
      message.success(`${label}任务成功`)
      await loadRuntimeSnapshot(detailTenant.agent_id)
    } catch (err) {
      message.error(err instanceof Error ? err.message : `${label}任务失败`)
    } finally {
      setCronActionLoading((prev) => ({ ...prev, [jobId]: false }))
    }
  }

  const handleSaveSystemPrompts = async (files: string[]) => {
    if (!detailTenant) return
    try {
      await putTenantSystemPrompts(detailTenant.agent_id, { files })
      message.success("Agent Prompt 文件已保存")
      await loadRuntimeSnapshot(detailTenant.agent_id)
    } catch (err) {
      message.error(err instanceof Error ? err.message : "保存 Prompt 文件失败")
    }
  }

  const handleApprovalLevelChange = async (approvalLevel: string) => {
    if (!detailTenant) return
    try {
      await putTenantSecuritySettings(detailTenant.agent_id, {
        approval_level: approvalLevel,
        tool_guard_rules: runtimeSnapshot.security?.tool_guard_rules || [],
      })
      message.success("Agent 安全等级已保存")
      await loadRuntimeSnapshot(detailTenant.agent_id)
    } catch (err) {
      message.error(err instanceof Error ? err.message : "保存安全等级失败")
    }
  }

  /** 格式化更新时间 */
  const formatTime = (time?: string | null) => {
    if (!time) return "-"
    return new Date(time).toLocaleString()
  }

  /** 表格列定义 */
  const columns: ColumnsType<WecomTenantSummary> = [
    {
      title: "租户 ID",
      dataIndex: "tenant_id",
      key: "tenant_id",
    },
    {
      title: "Agent ID",
      dataIndex: "agent_id",
      key: "agent_id",
    },
    {
      title: "状态",
      key: "status",
      render: (_, record) => {
        const display = getTenantDisplayStatus(record)
        return <Tag color={display.color}>{display.label}</Tag>
      },
    },
    {
      title: "会话数",
      dataIndex: "chat_count",
      key: "chat_count",
    },
    {
      title: "任务数",
      dataIndex: "job_count",
      key: "job_count",
    },
    {
      title: "更新时间",
      dataIndex: "updated_at",
      key: "updated_at",
      render: (val: string | null) => formatTime(val),
    },
    {
      title: "操作",
      key: "action",
      render: (_, record) => {
        const isLoading = actionLoading[record.agent_id] ?? false
        return (
          <Space size="small">
            {!record.running ? (
              <Button
                type="link"
                size="small"
                icon={<PlayCircleOutlined />}
                loading={isLoading}
                onClick={() => handleAction(record.agent_id, "start")}
                aria-label="启动"
              >
                启动
              </Button>
            ) : (
              <Button
                type="link"
                size="small"
                danger
                icon={<PauseCircleOutlined />}
                loading={isLoading}
                onClick={() => handleAction(record.agent_id, "stop")}
                aria-label="停止"
              >
                停止
              </Button>
            )}
            <Button
              type="link"
              size="small"
              icon={<ReloadOutlined />}
              loading={isLoading}
              onClick={() => handleAction(record.agent_id, "restart")}
              aria-label="重启"
            >
              重启
            </Button>
            <Button
              type="link"
              size="small"
              icon={<InfoCircleOutlined />}
              onClick={() => handleDetail(record)}
              aria-label="详情"
            >
              详情
            </Button>
          </Space>
        )
      },
    },
  ]

  const cronColumns: ColumnsType<TenantCronJob> = [
    {
      title: "任务",
      dataIndex: "name",
      key: "name",
      render: (value: string, record) => value || record.id || "-",
    },
    {
      title: "状态",
      dataIndex: "enabled",
      key: "enabled",
      render: (enabled: boolean) => (
        <Tag color={enabled ? "green" : "default"}>
          {enabled ? "启用" : "暂停"}
        </Tag>
      ),
    },
    {
      title: "类型",
      dataIndex: "task_type",
      key: "task_type",
      render: (value?: string) => value || "-",
    },
    {
      title: "操作",
      key: "action",
      render: (_, record) => {
        const jobId = record.id || ""
        const isLoading = cronActionLoading[jobId] ?? false
        return (
          <Space size="small">
            <Button
              type="link"
              size="small"
              disabled={!jobId}
              loading={isLoading}
              onClick={() => handleCronAction(jobId, record.enabled ? "pause" : "resume")}
            >
              {record.enabled ? "暂停" : "恢复"}
            </Button>
            <Button
              type="link"
              size="small"
              disabled={!jobId}
              loading={isLoading}
              onClick={() => handleCronAction(jobId, "run")}
            >
              运行
            </Button>
          </Space>
        )
      },
    },
  ]

  return (
    <div className="enterprise-page">
      {/* 页面头部 */}
      <div className="enterprise-page-header">
        <Title level={3} style={{ margin: 0 }}>
          租户管理
        </Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setCreateModalOpen(true)}
        >
          新建租户
        </Button>
      </div>

      <div style={{ marginBottom: 24 }}>
        <PageCompletenessPanel pageKey="tenants" compact />
      </div>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} className="enterprise-stat-grid">
        <Col xs={12} sm={8} lg={4}>
          <Card size="small">
            <Statistic title="租户总数" value={stats.total} />
          </Card>
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <Card size="small">
            <Statistic title="运行中" value={stats.running} />
          </Card>
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <Card size="small">
            <Statistic title="已初始化" value={stats.initialized} />
          </Card>
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <Card size="small">
            <Statistic title="会话数" value={stats.totalChats} />
          </Card>
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <Card size="small">
            <Statistic title="任务数" value={stats.totalJobs} />
          </Card>
        </Col>
      </Row>

      {/* 租户表格 */}
      <Card>
        {loading && tenants.length === 0 ? (
          <div style={{ textAlign: "center", padding: 48 }}>
            <Spin size="large" />
          </div>
        ) : (
          <Table
            rowKey="agent_id"
            columns={columns}
            dataSource={tenants}
            loading={loading}
            pagination={{ pageSize: 10 }}
          />
        )}
      </Card>

      {/* 新建租户弹窗 */}
      <Modal
        title="新建租户"
        open={createModalOpen}
        onCancel={() => {
          setCreateModalOpen(false)
          form.resetFields()
        }}
        onOk={() => form.submit()}
        confirmLoading={createLoading}
        okText="确认"
        cancelText="取消"
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreate}
          initialValues={{ startAfterCreate: false }}
        >
          <Form.Item
            name="tenant_id"
            label="租户 ID"
            rules={[{ required: true, message: "请输入租户 ID" }]}
          >
            <Input placeholder="例如: acme" />
          </Form.Item>
          <Form.Item
            name="startAfterCreate"
            label="创建后启动"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      {/* 租户详情抽屉 */}
      <Drawer
        title="租户详情"
        open={detailDrawerOpen}
        onClose={() => {
          setDetailDrawerOpen(false)
          setDetailTenant(null)
        }}
        width={480}
      >
        {detailTenant && (
          <Tabs
            defaultActiveKey="basic"
            items={[
              {
                key: "basic",
                label: "基础信息",
                children: (
                  <Descriptions column={1} bordered size="small">
                    <Descriptions.Item label="Agent ID">
                      {detailTenant.agent_id}
                    </Descriptions.Item>
                    <Descriptions.Item label="租户 ID">
                      {detailTenant.tenant_id}
                    </Descriptions.Item>
                    <Descriptions.Item label="工作空间">
                      {detailTenant.workspace_dir}
                    </Descriptions.Item>
                    <Descriptions.Item label="来源">
                      {detailTenant.source}
                    </Descriptions.Item>
                    <Descriptions.Item label="状态">
                      <Tag color={getTenantDisplayStatus(detailTenant).color}>
                        {getTenantDisplayStatus(detailTenant).label}
                      </Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label="更新时间">
                      {formatTime(detailTenant.updated_at)}
                    </Descriptions.Item>
                  </Descriptions>
                ),
              },
              {
                key: "entry",
                label: "入口配置",
                children: (
                  <Alert
                    type="info"
                    showIcon
                    message="阶段化开放"
                    description="企微回调、可信 IP、Bot 参数和 WebChat 会话设置将作为租户详情的入口配置能力逐步开放，当前先展示只读说明，待后端租户级配置契约成熟后再纳入可配置视图。"
                  />
                ),
              },
              {
                key: "agent-config",
                label: "Agent 配置",
                children: (
                  <Spin spinning={runtimeLoading}>
                    <Space direction="vertical" size="middle" style={{ width: "100%" }}>
                      <Card size="small" title="平台模板">
                        <List
                          size="small"
                          dataSource={runtimeSnapshot.templates}
                          locale={{ emptyText: "暂无模板" }}
                          renderItem={(item) => (
                            <List.Item>
                              <Space direction="vertical" size={0}>
                                <Typography.Text strong>
                                  {item.display_name || item.template_id}
                                </Typography.Text>
                                <Typography.Text type="secondary">
                                  {item.template_id}
                                  {item.default_model
                                    ? ` / ${item.default_model}`
                                    : ""}
                                </Typography.Text>
                              </Space>
                            </List.Item>
                          )}
                        />
                        <Alert
                          type="info"
                          showIcon
                          message="模板应用阶段化开放"
                          description="当前展示平台模板库存；将模板应用到租户 Agent 前仍需补齐差异预览、确认和审计闭环。"
                        />
                      </Card>
                      <Card size="small" title="Agent Prompt 文件">
                        <Select
                          mode="tags"
                          aria-label="Agent Prompt 文件"
                          style={{ width: "100%" }}
                          value={runtimeSnapshot.systemPrompts?.files || []}
                          onChange={handleSaveSystemPrompts}
                          options={[
                            { value: "AGENTS.md", label: "AGENTS.md" },
                            { value: "SOUL.md", label: "SOUL.md" },
                            { value: "PROFILE.md", label: "PROFILE.md" },
                          ]}
                        />
                      </Card>
                      <Card size="small" title="Agent 安全等级">
                        <Select
                          aria-label="Agent 安全等级"
                          style={{ width: "100%" }}
                          value={runtimeSnapshot.security?.approval_level || "AUTO"}
                          onChange={handleApprovalLevelChange}
                          options={[
                            { value: "STRICT", label: "STRICT" },
                            { value: "SMART", label: "SMART" },
                            { value: "AUTO", label: "AUTO" },
                            { value: "OFF", label: "OFF" },
                          ]}
                        />
                      </Card>
                    </Space>
                  </Spin>
                ),
              },
              {
                key: "runtime",
                label: "运行资源",
                children: (
                  <Spin spinning={runtimeLoading}>
                    <Space direction="vertical" size="middle" style={{ width: "100%" }}>
                      {runtimeError && (
                        <Alert
                          type="warning"
                          showIcon
                          message="运行资源加载失败"
                          description={runtimeError}
                        />
                      )}
                      <Card size="small" title="健康检查">
                        {runtimeSnapshot.health ? (
                          <Descriptions column={1} size="small">
                            <Descriptions.Item label="健康状态">
                              <Tag
                                color={
                                  runtimeSnapshot.health.status === "healthy"
                                    ? "green"
                                    : runtimeSnapshot.health.status === "degraded"
                                      ? "orange"
                                      : "red"
                                }
                              >
                                {runtimeSnapshot.health.status}
                              </Tag>
                            </Descriptions.Item>
                            {Object.entries(runtimeSnapshot.health.checks).map(
                              ([key, value]) => (
                                <Descriptions.Item key={key} label={key}>
                                  {String(value)}
                                </Descriptions.Item>
                              ),
                            )}
                          </Descriptions>
                        ) : (
                          <Alert type="info" showIcon message="暂无健康检查数据" />
                        )}
                      </Card>
                      <Card size="small" title="入口诊断">
                        {runtimeSnapshot.entryDiagnostics ? (
                          <Descriptions column={1} size="small">
                            <Descriptions.Item label="诊断状态">
                              <Tag
                                color={
                                  runtimeSnapshot.entryDiagnostics.status === "ok"
                                    ? "green"
                                    : "orange"
                                }
                              >
                                {runtimeSnapshot.entryDiagnostics.status}
                              </Tag>
                            </Descriptions.Item>
                            {Object.entries(
                              runtimeSnapshot.entryDiagnostics.checks,
                            ).map(([key, value]) => (
                              <Descriptions.Item key={key} label={key}>
                                {String(value)}
                              </Descriptions.Item>
                            ))}
                          </Descriptions>
                        ) : (
                          <Alert type="info" showIcon message="暂无入口诊断数据" />
                        )}
                      </Card>
                      <Card size="small" title="模型路由">
                        <Descriptions column={1} size="small">
                          <Descriptions.Item label="Active Model">
                            {runtimeSnapshot.model
                              ? `${runtimeSnapshot.model.provider_id} / ${runtimeSnapshot.model.model}`
                              : "未配置"}
                          </Descriptions.Item>
                          <Descriptions.Item label="路由状态">
                            {runtimeSnapshot.routing?.enabled ? "启用" : "未启用"}
                          </Descriptions.Item>
                          <Descriptions.Item label="路由模式">
                            {runtimeSnapshot.routing?.mode || "-"}
                          </Descriptions.Item>
                        </Descriptions>
                      </Card>
                      <Card size="small" title="Skills / MCP / Tools">
                        <Row gutter={[12, 12]}>
                          <Col span={8}>
                            <Statistic
                              title="Skills"
                              value={runtimeSnapshot.skills.length}
                            />
                          </Col>
                          <Col span={8}>
                            <Statistic
                              title="MCP"
                              value={runtimeSnapshot.mcpClients.length}
                            />
                          </Col>
                          <Col span={8}>
                            <Statistic
                              title="Tools"
                              value={runtimeSnapshot.tools.length}
                            />
                          </Col>
                        </Row>
                        <List
                          size="small"
                          dataSource={[
                            ...runtimeSnapshot.skills
                              .filter((item) => item.enabled)
                              .slice(0, 3)
                              .map((item) => `Skill: ${item.name}`),
                            ...runtimeSnapshot.mcpClients
                              .filter((item) => item.enabled)
                              .slice(0, 3)
                              .map((item) => `MCP: ${item.name || item.client_key}`),
                            ...runtimeSnapshot.tools
                              .filter((item) => item.enabled)
                              .slice(0, 3)
                              .map((item) => `Tool: ${item.name}`),
                          ]}
                          locale={{ emptyText: "暂无启用能力" }}
                          renderItem={(item) => <List.Item>{item}</List.Item>}
                        />
                      </Card>
                      <Card size="small" title="Workspace 文件">
                        <List
                          size="small"
                          dataSource={runtimeSnapshot.files}
                          locale={{ emptyText: "暂无文件" }}
                          renderItem={(item) => (
                            <List.Item>
                              <span>{item.filename}</span>
                              <Typography.Text type="secondary">
                                {item.size} bytes
                              </Typography.Text>
                            </List.Item>
                          )}
                        />
                      </Card>
                      <Card size="small" title="Memory 文件">
                        <List
                          size="small"
                          dataSource={runtimeSnapshot.memoryFiles}
                          locale={{ emptyText: "暂无记忆文件" }}
                          renderItem={(item) => (
                            <List.Item>
                              <span>{item.filename}</span>
                              <Typography.Text type="secondary">
                                {item.size} bytes
                              </Typography.Text>
                            </List.Item>
                          )}
                        />
                      </Card>
                      <Card size="small" title="自动化任务">
                        <Table
                          rowKey={(record) => record.id || record.name}
                          size="small"
                          columns={cronColumns}
                          dataSource={runtimeSnapshot.cronJobs}
                          pagination={false}
                        />
                      </Card>
                      <Card size="small" title="导入导出与模板">
                        <Alert
                          type="info"
                          showIcon
                          message="租户导出已由后端支持"
                          description={`可通过 /api/config/channels/wecom_tenant/tenants/${detailTenant.agent_id}/export 导出租户工作区；导入、模板应用和 dry-run 预览仍需显式确认后阶段化开放。`}
                        />
                      </Card>
                    </Space>
                  </Spin>
                ),
              },
              {
                key: "diagnostics",
                label: "诊断与审计",
                children: (
                  <Alert
                    type="info"
                    showIcon
                    message="只读阶段说明"
                    description="readiness、业务调用、审计事件和诊断关联能力后续会纳入该页签，当前阶段只提供只读说明，避免提前引入新的后端写契约。"
                  />
                ),
              },
            ]}
          />
        )}
      </Drawer>
    </div>
  )
}

export default TenantsPage
