import React, { useEffect, useState } from "react"
import {
  Alert,
  Button,
  Card,
  Form,
  Input,
  Select,
  Space,
  Switch,
  Typography,
  message,
} from "antd"
import {
  diagnoseTenantEntryConfig,
  getTenantEntryConfig,
  putTenantEntryConfig,
} from "@/api/entryConfig"
import { listWecomTenants } from "@/api/tenants"
import type { TenantEntryConfig, WecomTenantSummary } from "@/api/types"
import PageCompletenessPanel from "@/features/platform-readiness/PageCompletenessPanel"

const { Title, Text } = Typography

const defaultEntryConfig: TenantEntryConfig = {
  wecom: {
    enabled: false,
    bot_id: "",
    secret: "",
    secret_set: false,
    media_dir: null,
    welcome_text: "",
    share_session_in_group: true,
    max_reconnect_attempts: -1,
    streaming_enabled: false,
    require_mention: false,
    dm_policy: "open",
    group_policy: "open",
    allow_from: [],
    deny_message: "",
  },
  webchat: {
    enabled: false,
    media_dir: null,
    user_data_dir: null,
    require_mention: false,
    dm_policy: "open",
    group_policy: "open",
    allow_from: [],
    deny_message: "",
  },
}

function splitList(value: string | string[] | undefined): string[] {
  if (Array.isArray(value)) return value
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
}

function joinList(value: string[] | undefined): string {
  return (value || []).join(", ")
}

const EntryConfigPage: React.FC = () => {
  const [tenants, setTenants] = useState<WecomTenantSummary[]>([])
  const [selectedAgentId, setSelectedAgentId] = useState<string>()
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [diagnostics, setDiagnostics] = useState<string[]>([])
  const [form] = Form.useForm<TenantEntryConfig>()

  useEffect(() => {
    listWecomTenants()
      .then((response) => {
        setTenants(response.tenants)
        setSelectedAgentId(response.tenants[0]?.agent_id)
      })
      .catch((err: unknown) => {
        message.error(err instanceof Error ? err.message : "加载租户列表失败")
      })
  }, [])

  useEffect(() => {
    if (!selectedAgentId) return
    setLoading(true)
    getTenantEntryConfig(selectedAgentId)
      .then((config) => {
        form.setFieldsValue({
          ...defaultEntryConfig,
          ...config,
          wecom: {
            ...defaultEntryConfig.wecom,
            ...config.wecom,
            secret: "",
            allow_from: joinList(config.wecom.allow_from) as unknown as string[],
          },
          webchat: {
            ...defaultEntryConfig.webchat,
            ...config.webchat,
            allow_from: joinList(config.webchat.allow_from) as unknown as string[],
          },
        })
        setDiagnostics([])
      })
      .catch((err: unknown) => {
        message.error(err instanceof Error ? err.message : "加载入口配置失败")
      })
      .finally(() => setLoading(false))
  }, [form, selectedAgentId])

  const saveConfig = async (values: TenantEntryConfig) => {
    if (!selectedAgentId) return
    try {
      setSaving(true)
      await putTenantEntryConfig(selectedAgentId, {
        wecom: {
          ...values.wecom,
          allow_from: splitList(values.wecom.allow_from as unknown as string),
        },
        webchat: {
          ...values.webchat,
          allow_from: splitList(values.webchat.allow_from as unknown as string),
        },
      })
      message.success("入口配置已保存")
      const result = await diagnoseTenantEntryConfig(selectedAgentId)
      setDiagnostics(
        result.messages.length > 0
          ? result.messages
          : [`诊断状态：${result.status}`],
      )
    } catch (err) {
      message.error(err instanceof Error ? err.message : "保存入口配置失败")
    } finally {
      setSaving(false)
    }
  }

  const runDiagnostics = async () => {
    if (!selectedAgentId) return
    try {
      const result = await diagnoseTenantEntryConfig(selectedAgentId)
      setDiagnostics(
        result.messages.length > 0
          ? result.messages
          : [`诊断状态：${result.status}`],
      )
    } catch (err) {
      message.error(err instanceof Error ? err.message : "入口诊断失败")
    }
  }

  return (
    <div className="enterprise-page">
      <Space direction="vertical" size="large" style={{ width: "100%" }}>
        <Space
          align="start"
          style={{ width: "100%", justifyContent: "space-between" }}
        >
          <div>
            <Title level={3} style={{ margin: 0 }}>
              入口配置
            </Title>
            <Text type="secondary">企微 Bot 与 WebChat 租户入口治理</Text>
          </div>
          <Select
            aria-label="入口配置租户选择器"
            style={{ minWidth: 280 }}
            placeholder="选择租户"
            value={selectedAgentId}
            options={tenants.map((tenant) => ({
              label: `${tenant.tenant_id} / ${tenant.agent_id}`,
              value: tenant.agent_id,
            }))}
            onChange={setSelectedAgentId}
            disabled={tenants.length === 0}
          />
        </Space>

        <PageCompletenessPanel pageKey="entryConfig" compact />

        <Alert
          type="info"
          showIcon
          message="WebChat 平台级登录参数仍由环境变量管理"
          description="本页只写入租户工作区 agent.json 中的入口启停、白名单、会话共享和媒体目录等设置；WebChat SSO、二维码和 session secret 仍保持平台环境配置。"
        />

        {diagnostics.length > 0 && (
          <Alert type="success" showIcon message={diagnostics.join("；")} />
        )}

        <Card title="租户入口配置" loading={loading}>
          <Form
            form={form}
            layout="vertical"
            initialValues={defaultEntryConfig}
            onFinish={saveConfig}
          >
            <Title level={5}>企微 Bot</Title>
            <Form.Item name={["wecom", "enabled"]} label="启用" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item name={["wecom", "bot_id"]} label="WeCom Bot ID">
              <Input />
            </Form.Item>
            <Form.Item
              name={["wecom", "secret"]}
              label="WeCom Secret"
              extra="留空时保留当前已配置 Secret。"
            >
              <Input.Password placeholder="留空保留已有 Secret" />
            </Form.Item>
            <Form.Item name={["wecom", "welcome_text"]} label="欢迎语">
              <Input />
            </Form.Item>
            <Form.Item
              name={["wecom", "share_session_in_group"]}
              label="群聊共享会话"
              valuePropName="checked"
            >
              <Switch />
            </Form.Item>
            <Form.Item
              name={["wecom", "streaming_enabled"]}
              label="流式响应"
              valuePropName="checked"
            >
              <Switch />
            </Form.Item>
            <Form.Item name={["wecom", "allow_from"]} label="企微允许来源">
              <Input placeholder="corp-a, corp-b" />
            </Form.Item>

            <Title level={5}>WebChat</Title>
            <Form.Item name={["webchat", "enabled"]} label="启用" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item name={["webchat", "user_data_dir"]} label="用户数据目录">
              <Input />
            </Form.Item>
            <Form.Item name={["webchat", "media_dir"]} label="媒体目录">
              <Input />
            </Form.Item>
            <Form.Item name={["webchat", "dm_policy"]} label="私聊策略">
              <Select
                options={[
                  { value: "open", label: "open" },
                  { value: "allowlist", label: "allowlist" },
                ]}
              />
            </Form.Item>
            <Form.Item name={["webchat", "allow_from"]} label="WebChat 允许来源">
              <Input placeholder="user-a, user-b" />
            </Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={saving}>
                保存入口配置
              </Button>
              <Button onClick={runDiagnostics}>运行入口诊断</Button>
            </Space>
          </Form>
        </Card>
      </Space>
    </div>
  )
}

export default EntryConfigPage
