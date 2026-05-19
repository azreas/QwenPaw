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
  Tabs,
  Tag,
  Typography,
  message,
} from "antd"
import type { ColumnsType } from "antd/es/table"
import { ApiError } from "@/api/http"
import {
  createTenantMcpClient,
  deleteTenantSkill,
  deleteTenantMcpClient,
  installTenantSkill,
  listTenantMcpClients,
  listTenantSkills,
  listTenantTools,
  testTenantMcpClient,
  toggleTenantMcpClient,
  toggleTenantSkill,
  toggleTenantTool,
  updateTenantToolAsyncExecution,
} from "@/api/abilities"
import { listWecomTenants } from "@/api/tenants"
import type {
  MCPClientInfo,
  SkillInfo,
  ToolInfo,
  WecomTenantSummary,
} from "@/api/types"
import {
  buildAbilityStats,
  getAbilityStatusTag,
  getConnectionTestTag,
  getLastCallText,
} from "@/features/abilities/abilityModel"
import PageCompletenessPanel from "@/features/platform-readiness/PageCompletenessPanel"

const { Title, Text } = Typography

function getAbilitiesErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiError && err.isForbidden()) {
    return "当前身份无权管理租户能力或未绑定租户"
  }
  return err instanceof Error ? err.message : fallback
}

const AbilitiesPage: React.FC = () => {
  const [tenants, setTenants] = useState<WecomTenantSummary[]>([])
  const [selectedAgentId, setSelectedAgentId] = useState<string>()
  const [skills, setSkills] = useState<SkillInfo[]>([])
  const [mcpClients, setMcpClients] = useState<MCPClientInfo[]>([])
  const [tools, setTools] = useState<ToolInfo[]>([])
  const [tenantLoading, setTenantLoading] = useState(true)
  const [abilityLoading, setAbilityLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>({})
  const [mcpModalOpen, setMcpModalOpen] = useState(false)
  const [mcpForm] = Form.useForm<{
    client_key: string
    name: string
    command: string
    url: string
  }>()

  const loadAbilities = useCallback(async (agentId: string) => {
    try {
      setAbilityLoading(true)
      const [skillList, mcpList, toolList] = await Promise.all([
        listTenantSkills(agentId),
        listTenantMcpClients(agentId),
        listTenantTools(agentId),
      ])
      setSkills(skillList)
      setMcpClients(mcpList)
      setTools(toolList)
    } catch (err) {
      setSkills([])
      setMcpClients([])
      setTools([])
      message.error(getAbilitiesErrorMessage(err, "加载租户能力失败"))
    } finally {
      setAbilityLoading(false)
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
        setSkills([])
        setMcpClients([])
        setTools([])
        return
      }
      setSelectedAgentId((current) => {
        if (current && nextTenants.some((item) => item.agent_id === current)) {
          return current
        }
        return nextTenants[0].agent_id
      })
    } catch (err) {
      message.error(
        err instanceof Error ? err.message : "加载租户列表失败",
      )
      setTenants([])
      setSelectedAgentId(undefined)
      setSkills([])
      setMcpClients([])
      setTools([])
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
    void loadAbilities(selectedAgentId)
  }, [loadAbilities, selectedAgentId])

  const stats = useMemo(
    () => buildAbilityStats(skills, mcpClients, tools),
    [skills, mcpClients, tools],
  )

  const setBusy = (key: string, loading: boolean) => {
    setActionLoading((prev) => ({ ...prev, [key]: loading }))
  }

  const handleSkillToggle = async (skill: SkillInfo) => {
    if (!selectedAgentId) return
    const key = `skill:${skill.name}`
    try {
      setBusy(key, true)
      await toggleTenantSkill(selectedAgentId, skill.name)
      await loadAbilities(selectedAgentId)
    } catch (err) {
      message.error(getAbilitiesErrorMessage(err, "切换 Skill 状态失败"))
    } finally {
      setBusy(key, false)
    }
  }

  const handleSkillInstall = async (skill: SkillInfo) => {
    if (!selectedAgentId) return
    const key = `skill-install:${skill.name}`
    try {
      setBusy(key, true)
      await installTenantSkill(selectedAgentId, {
        skill_id: skill.name,
        overwrite: false,
      })
      await loadAbilities(selectedAgentId)
    } catch (err) {
      message.error(getAbilitiesErrorMessage(err, "安装 Skill 失败"))
    } finally {
      setBusy(key, false)
    }
  }

  const handleSkillDelete = async (skill: SkillInfo) => {
    if (!selectedAgentId) return
    const key = `skill-delete:${skill.name}`
    try {
      setBusy(key, true)
      await deleteTenantSkill(selectedAgentId, skill.name)
      await loadAbilities(selectedAgentId)
    } catch (err) {
      message.error(getAbilitiesErrorMessage(err, "删除 Skill 失败"))
    } finally {
      setBusy(key, false)
    }
  }

  const handleMcpToggle = async (client: MCPClientInfo) => {
    if (!selectedAgentId) return
    const key = `mcp:${client.client_key}`
    try {
      setBusy(key, true)
      await toggleTenantMcpClient(selectedAgentId, client.client_key)
      await loadAbilities(selectedAgentId)
    } catch (err) {
      message.error(getAbilitiesErrorMessage(err, "切换 MCP 状态失败"))
    } finally {
      setBusy(key, false)
    }
  }

  const handleMcpTest = async (client: MCPClientInfo) => {
    if (!selectedAgentId) return
    const key = `test:${client.client_key}`
    try {
      setBusy(key, true)
      await testTenantMcpClient(selectedAgentId, client.client_key)
      await loadAbilities(selectedAgentId)
    } catch (err) {
      message.error(getAbilitiesErrorMessage(err, "测试 MCP 连接失败"))
    } finally {
      setBusy(key, false)
    }
  }

  const handleMcpCreate = async (values: {
    client_key: string
    name: string
    command: string
    url: string
  }) => {
    if (!selectedAgentId) return
    try {
      setBusy("mcp-create", true)
      await createTenantMcpClient(selectedAgentId, {
        client_key: values.client_key,
        client: {
          name: values.name,
          command: values.command,
          url: values.url,
        },
      })
      setMcpModalOpen(false)
      mcpForm.resetFields()
      await loadAbilities(selectedAgentId)
    } catch (err) {
      message.error(getAbilitiesErrorMessage(err, "创建 MCP 失败"))
    } finally {
      setBusy("mcp-create", false)
    }
  }

  const handleMcpDelete = async (client: MCPClientInfo) => {
    if (!selectedAgentId) return
    const key = `mcp-delete:${client.client_key}`
    try {
      setBusy(key, true)
      await deleteTenantMcpClient(selectedAgentId, client.client_key)
      await loadAbilities(selectedAgentId)
    } catch (err) {
      message.error(getAbilitiesErrorMessage(err, "删除 MCP 失败"))
    } finally {
      setBusy(key, false)
    }
  }

  const handleToolToggle = async (tool: ToolInfo) => {
    if (!selectedAgentId) return
    const key = `tool:${tool.name}`
    try {
      setBusy(key, true)
      await toggleTenantTool(selectedAgentId, tool.name)
      await loadAbilities(selectedAgentId)
    } catch (err) {
      message.error(getAbilitiesErrorMessage(err, "切换 Tool 状态失败"))
    } finally {
      setBusy(key, false)
    }
  }

  const handleToolAsyncToggle = async (tool: ToolInfo) => {
    if (!selectedAgentId) return
    const key = `tool-async:${tool.name}`
    try {
      setBusy(key, true)
      await updateTenantToolAsyncExecution(selectedAgentId, tool.name, {
        async_execution: !tool.async_execution,
      })
      await loadAbilities(selectedAgentId)
    } catch (err) {
      message.error(getAbilitiesErrorMessage(err, "切换 Tool 异步执行失败"))
    } finally {
      setBusy(key, false)
    }
  }

  const skillColumns: ColumnsType<SkillInfo> = [
    {
      title: "名称",
      dataIndex: "name",
      key: "name",
    },
    {
      title: "来源",
      dataIndex: "source",
      key: "source",
    },
    {
      title: "状态",
      key: "status",
      render: (_, record) => {
        const status = getAbilityStatusTag(record.enabled)
        return <Tag color={status.color}>{status.text}</Tag>
      },
    },
    {
      title: "标签",
      dataIndex: "tags",
      key: "tags",
      render: (tags: string[]) =>
        tags.length > 0 ? (
          <Space wrap>
            {tags.map((tag) => (
              <Tag key={tag}>{tag}</Tag>
            ))}
          </Space>
        ) : (
          "-"
        ),
    },
    {
      title: "最近调用",
      key: "last_call",
      render: (_, record) => getLastCallText(record),
    },
    {
      title: "操作",
      key: "action",
      render: (_, record) => {
        if (!record.installed && record.installable) {
          return (
            <Button
              type="link"
              size="small"
              loading={actionLoading[`skill-install:${record.name}`] ?? false}
              aria-label={`安装 ${record.name}`}
              onClick={() => void handleSkillInstall(record)}
            >
              安装
            </Button>
          )
        }
        const actionLabel = record.enabled ? "停用" : "启用"
        return (
          <Space size="small">
            <Button
              type="link"
              size="small"
              loading={actionLoading[`skill:${record.name}`] ?? false}
              aria-label={`${actionLabel} ${record.name}`}
              onClick={() => void handleSkillToggle(record)}
            >
              {actionLabel}
            </Button>
            <Button
              danger
              type="link"
              size="small"
              loading={actionLoading[`skill-delete:${record.name}`] ?? false}
              aria-label={`删除 ${record.name}`}
              onClick={() => void handleSkillDelete(record)}
            >
              删除
            </Button>
          </Space>
        )
      },
    },
  ]

  const toolColumns: ColumnsType<ToolInfo> = [
    {
      title: "名称",
      dataIndex: "name",
      key: "name",
    },
    {
      title: "说明",
      dataIndex: "description",
      key: "description",
      render: (value: string) => value || "-",
    },
    {
      title: "状态",
      key: "status",
      render: (_, record) => {
        const status = getAbilityStatusTag(record.enabled)
        return <Tag color={status.color}>{status.text}</Tag>
      },
    },
    {
      title: "异步执行",
      dataIndex: "async_execution",
      key: "async_execution",
      render: (value: boolean) => (
        <Tag color={value ? "blue" : "default"}>{value ? "启用" : "关闭"}</Tag>
      ),
    },
    {
      title: "操作",
      key: "action",
      render: (_, record) => {
        const actionLabel = record.enabled ? "停用" : "启用"
        return (
          <Space size="small">
            <Button
              type="link"
              size="small"
              loading={actionLoading[`tool:${record.name}`] ?? false}
              aria-label={`${actionLabel} Tool ${record.name}`}
              onClick={() => void handleToolToggle(record)}
            >
              {actionLabel}
            </Button>
            <Button
              type="link"
              size="small"
              loading={actionLoading[`tool-async:${record.name}`] ?? false}
              aria-label={`切换异步 ${record.name}`}
              onClick={() => void handleToolAsyncToggle(record)}
            >
              异步
            </Button>
          </Space>
        )
      },
    },
  ]

  const mcpColumns: ColumnsType<MCPClientInfo> = [
    {
      title: "Client Key",
      dataIndex: "client_key",
      key: "client_key",
    },
    {
      title: "名称",
      dataIndex: "name",
      key: "name",
    },
    {
      title: "Transport",
      dataIndex: "transport",
      key: "transport",
    },
    {
      title: "状态",
      key: "status",
      render: (_, record) => {
        const status = getAbilityStatusTag(record.enabled)
        return <Tag color={status.color}>{status.text}</Tag>
      },
    },
    {
      title: "连接测试",
      key: "connection_test",
      render: (_, record) => {
        const status = getConnectionTestTag(record.last_test_status)
        return <Tag color={status.color}>{status.text}</Tag>
      },
    },
    {
      title: "最近调用",
      key: "last_call",
      render: (_, record) => getLastCallText(record),
    },
    {
      title: "操作",
      key: "action",
      render: (_, record) => {
        const actionLabel = record.enabled ? "停用" : "启用"
        return (
          <Space size="small">
            <Button
              type="link"
              size="small"
              loading={actionLoading[`mcp:${record.client_key}`] ?? false}
              aria-label={`${actionLabel} ${record.client_key}`}
              onClick={() => void handleMcpToggle(record)}
            >
              {actionLabel}
            </Button>
            <Button
              type="link"
              size="small"
              loading={actionLoading[`test:${record.client_key}`] ?? false}
              aria-label={`测试 ${record.client_key}`}
              onClick={() => void handleMcpTest(record)}
            >
              测试
            </Button>
            <Button
              danger
              type="link"
              size="small"
              loading={actionLoading[`mcp-delete:${record.client_key}`] ?? false}
              aria-label={`删除 MCP ${record.client_key}`}
              onClick={() => void handleMcpDelete(record)}
            >
              删除
            </Button>
          </Space>
        )
      },
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Space
        direction="vertical"
        size="large"
        style={{ width: "100%" }}
      >
        <Space
          align="start"
          style={{ width: "100%", justifyContent: "space-between" }}
        >
          <div>
            <Title level={3} style={{ margin: 0 }}>
              业务能力
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

        <PageCompletenessPanel pageKey="abilities" compact />

        <Row gutter={[16, 16]}>
          <Col xs={12} sm={8} lg={4}>
            <Card size="small">
              <Statistic title="Skills 总数" value={stats.totalSkills} />
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={4}>
            <Card size="small">
              <Statistic title="已启用 Skills" value={stats.enabledSkills} />
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={4}>
            <Card size="small">
              <Statistic title="可安装 Skills" value={stats.installableSkills} />
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={4}>
            <Card size="small">
              <Statistic title="MCP 总数" value={stats.totalMcpClients} />
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={4}>
            <Card size="small">
              <Statistic title="已启用 MCP" value={stats.enabledMcpClients} />
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={4}>
            <Card size="small">
              <Statistic title="Tools 总数" value={stats.totalTools} />
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={4}>
            <Card size="small">
              <Statistic title="失败调用" value={stats.failedCalls} />
            </Card>
          </Col>
        </Row>

        <Card>
          {tenants.length === 0 && !tenantLoading ? (
            <Text>暂无租户</Text>
          ) : (
            <Tabs
              defaultActiveKey="skills"
              items={[
                {
                  key: "skills",
                  label: "Skills",
                  children: (
                    <Table
                      rowKey="name"
                      columns={skillColumns}
                      dataSource={skills}
                      loading={abilityLoading}
                      pagination={false}
                    />
                  ),
                },
                {
                  key: "mcp",
                  label: "MCP",
                  children: (
                    <Space direction="vertical" style={{ width: "100%" }}>
                      <Button type="primary" onClick={() => setMcpModalOpen(true)}>
                        新建 MCP
                      </Button>
                      <Table
                        rowKey="client_key"
                        columns={mcpColumns}
                        dataSource={mcpClients}
                        loading={abilityLoading}
                        pagination={false}
                      />
                    </Space>
                  ),
                },
                {
                  key: "catalog",
                  label: "能力目录",
                  children: (
                    <Alert
                      type="info"
                      showIcon
                      message="阶段化开放"
                      description="全局能力目录、版本、依赖校验和安全扫描。当前仅提供只读预览，暂不开放写入。"
                    />
                  ),
                },
                {
                  key: "tools",
                  label: "Tools",
                  children: (
                    <Table
                      rowKey="name"
                      columns={toolColumns}
                      dataSource={tools}
                      loading={abilityLoading}
                      pagination={false}
                    />
                  ),
                },
              ]}
            />
          )}
        </Card>
      </Space>
      <Modal
        title="新建 MCP"
        open={mcpModalOpen}
        onCancel={() => {
          setMcpModalOpen(false)
          mcpForm.resetFields()
        }}
        onOk={() => mcpForm.submit()}
        confirmLoading={actionLoading["mcp-create"] ?? false}
      >
        <Form form={mcpForm} layout="vertical" onFinish={handleMcpCreate}>
          <Form.Item
            name="client_key"
            label="Client Key"
            rules={[{ required: true, message: "请输入 Client Key" }]}
          >
            <Input placeholder="erp" />
          </Form.Item>
          <Form.Item
            name="name"
            label="名称"
            rules={[{ required: true, message: "请输入名称" }]}
          >
            <Input placeholder="ERP MCP" />
          </Form.Item>
          <Form.Item name="command" label="命令">
            <Input placeholder="uvx mcp-server" />
          </Form.Item>
          <Form.Item name="url" label="URL">
            <Input placeholder="https://mcp.example.com" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default AbilitiesPage
