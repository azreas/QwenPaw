import React, { useCallback, useEffect, useState } from "react"
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
  getTenantLlmRouting,
  getTenantModel,
  putTenantLlmRouting,
  putTenantModel,
} from "@/api/models"
import { listWecomTenants } from "@/api/tenants"
import type {
  AgentsLLMRoutingConfig,
  ModelSlotConfig,
  WecomTenantSummary,
} from "@/api/types"
import PageCompletenessPanel from "@/features/platform-readiness/PageCompletenessPanel"

const { Title, Text } = Typography

const emptyModel: ModelSlotConfig = { provider_id: "", model: "" }

function normalizeRouting(value?: AgentsLLMRoutingConfig | null): AgentsLLMRoutingConfig {
  return {
    enabled: value?.enabled ?? false,
    mode: value?.mode || "cloud_first",
    local: value?.local ?? emptyModel,
    cloud: value?.cloud ?? emptyModel,
  }
}

const ModelsPage: React.FC = () => {
  const [tenants, setTenants] = useState<WecomTenantSummary[]>([])
  const [selectedAgentId, setSelectedAgentId] = useState<string>()
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [modelForm] = Form.useForm<ModelSlotConfig>()
  const [routingForm] = Form.useForm<AgentsLLMRoutingConfig>()

  const loadModelState = useCallback(
    async (agentId: string) => {
      try {
        setLoading(true)
        const [activeModel, routing] = await Promise.all([
          getTenantModel(agentId),
          getTenantLlmRouting(agentId),
        ])
        modelForm.setFieldsValue(activeModel ?? emptyModel)
        routingForm.setFieldsValue(normalizeRouting(routing))
      } catch (err) {
        message.error(err instanceof Error ? err.message : "加载模型配置失败")
      } finally {
        setLoading(false)
      }
    },
    [modelForm, routingForm],
  )

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
    if (selectedAgentId) {
      void loadModelState(selectedAgentId)
    }
  }, [loadModelState, selectedAgentId])

  const saveModel = async (values: ModelSlotConfig) => {
    if (!selectedAgentId) return
    try {
      setSaving(true)
      await putTenantModel(selectedAgentId, values)
      message.success("模型配置已保存")
      await loadModelState(selectedAgentId)
    } catch (err) {
      message.error(err instanceof Error ? err.message : "保存模型配置失败")
    } finally {
      setSaving(false)
    }
  }

  const saveRouting = async (values: AgentsLLMRoutingConfig) => {
    if (!selectedAgentId) return
    try {
      setSaving(true)
      await putTenantLlmRouting(selectedAgentId, normalizeRouting(values))
      message.success("模型路由已保存")
      await loadModelState(selectedAgentId)
    } catch (err) {
      message.error(err instanceof Error ? err.message : "保存模型路由失败")
    } finally {
      setSaving(false)
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
              模型治理
            </Title>
            <Text type="secondary">租户模型授权与模型路由</Text>
          </div>
          <Space direction="vertical" size={4} style={{ minWidth: 280 }}>
            <Text>租户</Text>
            <Select
              aria-label="模型租户选择器"
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
        </Space>

        <PageCompletenessPanel pageKey="models" compact />

        <Alert
          type="info"
          showIcon
          message="平台模型库存阶段化开放"
          description="当前页面先开放租户级 active model 与 LLM routing 配置。平台模型库存、模型发现和跨租户授权矩阵仍按阶段化能力呈现。"
        />

        <Card title="Active Model" loading={loading}>
          <Form form={modelForm} layout="vertical" onFinish={saveModel}>
            <Form.Item
              name="provider_id"
              label="Provider ID"
              rules={[{ required: true, message: "请输入 Provider ID" }]}
            >
              <Input placeholder="dashscope" />
            </Form.Item>
            <Form.Item
              name="model"
              label="Model"
              rules={[{ required: true, message: "请输入 Model" }]}
            >
              <Input placeholder="qwen-max" />
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={saving}>
              保存 Active Model
            </Button>
          </Form>
        </Card>

        <Card title="LLM Routing" loading={loading}>
          <Form form={routingForm} layout="vertical" onFinish={saveRouting}>
            <Form.Item name="enabled" label="启用路由" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item name="mode" label="路由模式">
              <Select
                options={[
                  { value: "cloud_first", label: "cloud_first" },
                  { value: "local_first", label: "local_first" },
                  { value: "local_only", label: "local_only" },
                  { value: "cloud_only", label: "cloud_only" },
                ]}
              />
            </Form.Item>
            <Form.Item name={["local", "provider_id"]} label="Local Provider">
              <Input placeholder="ollama" />
            </Form.Item>
            <Form.Item name={["local", "model"]} label="Local Model">
              <Input placeholder="qwen2.5" />
            </Form.Item>
            <Form.Item name={["cloud", "provider_id"]} label="Cloud Provider">
              <Input placeholder="dashscope" />
            </Form.Item>
            <Form.Item name={["cloud", "model"]} label="Cloud Model">
              <Input placeholder="qwen-max" />
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={saving}>
              保存模型路由
            </Button>
          </Form>
        </Card>
      </Space>
    </div>
  )
}

export default ModelsPage
