import React, { useCallback, useEffect, useMemo, useState } from "react"
import {
  Alert,
  Button,
  Card,
  Col,
  Form,
  Input,
  InputNumber,
  List,
  Row,
  Space,
  Statistic,
  Switch,
  Tabs,
  Tag,
  Typography,
  message,
} from "antd"
import {
  deletePolicy,
  deleteTemplate,
  listPlatformTenants,
  listPolicies,
  listTemplates,
  savePolicy,
  saveTemplate,
} from "@/api/policies"
import type {
  PlatformTenantRecord,
  TenantPolicy,
  TenantTemplate,
} from "@/api/types"
import PageCompletenessPanel from "@/features/platform-readiness/PageCompletenessPanel"

const { Title, Text } = Typography
const { TextArea } = Input

type PolicyFormValues = Omit<
  TenantPolicy,
  "allowed_models" | "allowed_tools" | "allowed_mcp_transports"
> & {
  allowed_models_text: string
  allowed_tools_text: string
  allowed_mcp_transports_text: string
}

type TemplateFormValues = Omit<
  TenantTemplate,
  | "default_model"
  | "default_prompt_files"
  | "default_skills"
  | "default_tools"
  | "default_task_templates"
> & {
  default_model: string
  default_prompt_files_text: string
  default_skills_text: string
  default_tools_text: string
  default_task_templates_text: string
}

const newPolicy: TenantPolicy = {
  policy_id: "new-policy",
  display_name: "新建成员策略",
  allow_model_switch: true,
  allowed_models: [],
  allow_skill_create: true,
  allow_skill_upload_zip: true,
  allow_skill_hub_import: true,
  allow_tools: true,
  allowed_tools: [],
  allow_mcp: true,
  allowed_mcp_transports: ["sse", "http"],
  allow_tasks: true,
  max_cron_jobs: 20,
  min_cron_interval_minutes: 5,
  allow_task_run_now: true,
  allow_task_tools: true,
  task_timeout_seconds: 120,
  file_upload_limit_mb: 100,
  token_quota_monthly: null,
  advanced_config_enabled: false,
}

const newTemplate: TenantTemplate = {
  template_id: "new-template",
  display_name: "新建成员模板",
  default_model: null,
  default_prompt_files: [],
  default_skills: [],
  default_tools: [],
  default_task_templates: [],
}

function toTextList(items: string[]): string {
  return items.join(", ")
}

function fromTextList(value?: string): string[] {
  return (value ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
}

function policyToForm(policy: TenantPolicy): PolicyFormValues {
  return {
    ...policy,
    allowed_models_text: toTextList(policy.allowed_models),
    allowed_tools_text: toTextList(policy.allowed_tools),
    allowed_mcp_transports_text: toTextList(policy.allowed_mcp_transports),
  }
}

function formToPolicy(values: PolicyFormValues, basePolicy: TenantPolicy): TenantPolicy {
  const {
    allowed_models_text,
    allowed_tools_text,
    allowed_mcp_transports_text,
    ...policyValues
  } = values
  return {
    ...basePolicy,
    ...policyValues,
    policy_id: values.policy_id.trim(),
    display_name: values.display_name.trim(),
    allowed_models: fromTextList(allowed_models_text),
    allowed_tools: fromTextList(allowed_tools_text),
    allowed_mcp_transports: fromTextList(allowed_mcp_transports_text),
    token_quota_monthly: values.token_quota_monthly ?? null,
  }
}

function templateToForm(template: TenantTemplate): TemplateFormValues {
  return {
    template_id: template.template_id,
    display_name: template.display_name,
    default_model: template.default_model ?? "",
    default_prompt_files_text: toTextList(template.default_prompt_files),
    default_skills_text: toTextList(template.default_skills),
    default_tools_text: toTextList(template.default_tools),
    default_task_templates_text: JSON.stringify(
      template.default_task_templates,
      null,
      2,
    ),
  }
}

function parseTaskTemplates(value: string): Record<string, unknown>[] {
  try {
    const parsed = JSON.parse(value || "[]")
    if (!Array.isArray(parsed)) {
      throw new Error("任务模板必须是 JSON 数组")
    }
    return parsed
  } catch {
    throw new Error("任务模板必须是 JSON 数组")
  }
}

function formToTemplate(values: TemplateFormValues): TenantTemplate {
  return {
    template_id: values.template_id.trim(),
    display_name: values.display_name.trim(),
    default_model: values.default_model.trim() || null,
    default_prompt_files: fromTextList(values.default_prompt_files_text),
    default_skills: fromTextList(values.default_skills_text),
    default_tools: fromTextList(values.default_tools_text),
    default_task_templates: parseTaskTemplates(values.default_task_templates_text),
  }
}

const PoliciesPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState("policies")
  const [policies, setPolicies] = useState<TenantPolicy[]>([])
  const [templates, setTemplates] = useState<TenantTemplate[]>([])
  const [tenants, setTenants] = useState<PlatformTenantRecord[]>([])
  const [selectedPolicyId, setSelectedPolicyId] = useState("")
  const [selectedTemplateId, setSelectedTemplateId] = useState("")
  const [policyDraft, setPolicyDraft] = useState<TenantPolicy | null>(null)
  const [templateDraft, setTemplateDraft] = useState<TenantTemplate | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [templateError, setTemplateError] = useState("")
  const [messageApi, contextHolder] = message.useMessage()

  const loadState = useCallback(async () => {
    try {
      setLoading(true)
      const [policyResp, templateResp, tenantResp] = await Promise.all([
        listPolicies(),
        listTemplates(),
        listPlatformTenants(),
      ])
      setPolicies(policyResp.policies)
      setTemplates(templateResp.templates)
      setTenants(tenantResp.tenants)
      setSelectedPolicyId((current) => {
        if (policyResp.policies.some((policy) => policy.policy_id === current)) {
          return current
        }
        return policyResp.policies[0]?.policy_id ?? ""
      })
      setSelectedTemplateId((current) => {
        if (
          templateResp.templates.some(
            (template) => template.template_id === current,
          )
        ) {
          return current
        }
        return templateResp.templates[0]?.template_id ?? ""
      })
    } catch (err) {
      messageApi.error(err instanceof Error ? err.message : "加载策略配置失败")
    } finally {
      setLoading(false)
    }
  }, [messageApi])

  useEffect(() => {
    void loadState()
  }, [loadState])

  const selectedPolicy = useMemo(
    () =>
      policyDraft ??
      policies.find((policy) => policy.policy_id === selectedPolicyId) ??
      null,
    [policies, policyDraft, selectedPolicyId],
  )

  const selectedTemplate = useMemo(
    () =>
      templateDraft ??
      templates.find((template) => template.template_id === selectedTemplateId) ??
      null,
    [selectedTemplateId, templateDraft, templates],
  )

  const policyReferences = useMemo(
    () =>
      selectedPolicy
        ? tenants.filter((tenant) => tenant.policy_id === selectedPolicy.policy_id)
        : [],
    [selectedPolicy, tenants],
  )

  const templateReferences = useMemo(
    () =>
      selectedTemplate
        ? tenants.filter(
            (tenant) => tenant.template_id === selectedTemplate.template_id,
          )
        : [],
    [selectedTemplate, tenants],
  )

  const referencedItemCount = useMemo(() => {
    const referencedPolicies = new Set(tenants.map((tenant) => tenant.policy_id))
    const referencedTemplates = new Set(tenants.map((tenant) => tenant.template_id))
    return (
      policies.filter((policy) => referencedPolicies.has(policy.policy_id)).length +
      templates.filter((template) =>
        referencedTemplates.has(template.template_id),
      ).length
    )
  }, [policies, templates, tenants])

  const deletableItemCount = useMemo(() => {
    const referencedPolicies = new Set(tenants.map((tenant) => tenant.policy_id))
    const referencedTemplates = new Set(tenants.map((tenant) => tenant.template_id))
    return (
      policies.filter(
        (policy) =>
          policy.policy_id !== "default" && !referencedPolicies.has(policy.policy_id),
      ).length +
      templates.filter(
        (template) =>
          template.template_id !== "default" &&
          !referencedTemplates.has(template.template_id),
      ).length
    )
  }, [policies, templates, tenants])

  const policyDeleteReason = policyDraft
    ? "新建项保存后可被租户引用"
    : selectedPolicy?.policy_id === "default"
      ? "默认项不可删除"
      : policyReferences.length > 0
        ? `仍被 ${policyReferences.length} 个租户引用`
        : ""

  const templateDeleteReason = templateDraft
    ? "新建项保存后可被租户引用"
    : selectedTemplate?.template_id === "default"
      ? "默认项不可删除"
      : templateReferences.length > 0
        ? `仍被 ${templateReferences.length} 个租户引用`
        : ""

  const isPolicyIdEditable = Boolean(policyDraft)
  const isTemplateIdEditable = Boolean(templateDraft)

  useEffect(() => {
    if (selectedTemplate) {
      setTemplateError("")
    }
  }, [selectedTemplate])

  const handleSavePolicy = async (values: PolicyFormValues) => {
    if (!selectedPolicy) {
      return
    }
    try {
      setSaving(true)
      const payload = formToPolicy(values, selectedPolicy)
      await savePolicy(payload.policy_id, payload)
      messageApi.success("策略已保存")
      setPolicyDraft(null)
      await loadState()
      setSelectedPolicyId(payload.policy_id)
    } catch (err) {
      messageApi.error(err instanceof Error ? err.message : "保存策略失败")
    } finally {
      setSaving(false)
    }
  }

  const handleDeletePolicy = async () => {
    if (!selectedPolicy || policyDeleteReason) {
      return
    }
    try {
      setSaving(true)
      await deletePolicy(selectedPolicy.policy_id)
      messageApi.success("策略已删除")
      setPolicyDraft(null)
      await loadState()
    } catch (err) {
      messageApi.error(err instanceof Error ? err.message : "删除策略失败")
    } finally {
      setSaving(false)
    }
  }

  const handleSaveTemplate = async (values: TemplateFormValues) => {
    if (!selectedTemplate) {
      return
    }
    try {
      setSaving(true)
      const payload = formToTemplate(values)
      setTemplateError("")
      await saveTemplate(payload.template_id, payload)
      messageApi.success("模板已保存")
      setTemplateDraft(null)
      await loadState()
      setSelectedTemplateId(payload.template_id)
    } catch (err) {
      const msg = err instanceof Error ? err.message : "保存模板失败"
      setTemplateError(msg)
      messageApi.error(msg)
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteTemplate = async () => {
    if (!selectedTemplate || templateDeleteReason) {
      return
    }
    try {
      setSaving(true)
      await deleteTemplate(selectedTemplate.template_id)
      messageApi.success("模板已删除")
      setTemplateDraft(null)
      await loadState()
    } catch (err) {
      messageApi.error(err instanceof Error ? err.message : "删除模板失败")
    } finally {
      setSaving(false)
    }
  }

  const selectPolicy = (policyId: string) => {
    setPolicyDraft(null)
    setSelectedPolicyId(policyId)
  }

  const selectTemplate = (templateId: string) => {
    setTemplateDraft(null)
    setSelectedTemplateId(templateId)
  }

  const startNewPolicy = () => {
    setPolicyDraft(newPolicy)
    setSelectedPolicyId(newPolicy.policy_id)
  }

  const startNewTemplate = () => {
    setTemplateDraft(newTemplate)
    setSelectedTemplateId(newTemplate.template_id)
  }

  const policyTab = (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={9}>
        <Card
          title="策略列表"
          loading={loading}
          extra={<Button onClick={startNewPolicy}>新建策略</Button>}
        >
          <List
            dataSource={policies}
            locale={{ emptyText: "暂无策略" }}
            renderItem={(policy) => (
              <List.Item>
                <Button
                  type="text"
                  style={{
                    paddingInline: 0,
                    textAlign: "left",
                    width: "100%",
                    height: "auto",
                  }}
                  onClick={() => selectPolicy(policy.policy_id)}
                >
                  <Space direction="vertical" size={0}>
                    <Text strong>{policy.display_name}</Text>
                    <Text type="secondary">{policy.policy_id}</Text>
                  </Space>
                </Button>
              </List.Item>
            )}
          />
        </Card>
      </Col>
      <Col xs={24} xl={15}>
        <Card title="策略详情" loading={loading}>
          <Form<PolicyFormValues>
            key={selectedPolicy?.policy_id ?? "empty-policy"}
            initialValues={selectedPolicy ? policyToForm(selectedPolicy) : undefined}
            layout="vertical"
            name="policyConfig"
            onFinish={handleSavePolicy}
          >
            <Row gutter={12}>
              <Col xs={24} md={12}>
                <Form.Item
                  label="策略 ID"
                  name="policy_id"
                  rules={[{ required: true, message: "请输入策略 ID" }]}
                >
                  <Input aria-label="策略 ID" disabled={!isPolicyIdEditable} />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item
                  label="策略名称"
                  name="display_name"
                  rules={[{ required: true, message: "请输入策略名称" }]}
                >
                  <Input aria-label="策略名称" />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item label="允许模型" name="allowed_models_text">
                  <Input aria-label="允许模型" placeholder="qwen-max, qwen-plus" />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item label="允许工具" name="allowed_tools_text">
                  <Input aria-label="允许工具" placeholder="read_file, search" />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item label="MCP Transport" name="allowed_mcp_transports_text">
                  <Input placeholder="sse, http" />
                </Form.Item>
              </Col>
              <Col xs={12} md={6}>
                <Form.Item label="Cron 上限" name="max_cron_jobs">
                  <InputNumber min={0} style={{ width: "100%" }} />
                </Form.Item>
              </Col>
              <Col xs={12} md={6}>
                <Form.Item label="最小间隔" name="min_cron_interval_minutes">
                  <InputNumber min={1} style={{ width: "100%" }} />
                </Form.Item>
              </Col>
              <Col xs={12} md={6}>
                <Form.Item label="任务超时" name="task_timeout_seconds">
                  <InputNumber min={1} style={{ width: "100%" }} />
                </Form.Item>
              </Col>
              <Col xs={12} md={6}>
                <Form.Item label="文件上限 MB" name="file_upload_limit_mb">
                  <InputNumber min={1} style={{ width: "100%" }} />
                </Form.Item>
              </Col>
              <Col xs={12} md={6}>
                <Form.Item label="月 Token 配额" name="token_quota_monthly">
                  <InputNumber min={0} style={{ width: "100%" }} />
                </Form.Item>
              </Col>
            </Row>
            <Space wrap>
              <Form.Item name="allow_model_switch" valuePropName="checked">
                <Switch checkedChildren="模型切换" unCheckedChildren="模型切换" />
              </Form.Item>
              <Form.Item name="allow_skill_create" valuePropName="checked">
                <Switch checkedChildren="创建 Skill" unCheckedChildren="创建 Skill" />
              </Form.Item>
              <Form.Item name="allow_tools" valuePropName="checked">
                <Switch checkedChildren="Tools" unCheckedChildren="Tools" />
              </Form.Item>
              <Form.Item name="allow_mcp" valuePropName="checked">
                <Switch checkedChildren="MCP" unCheckedChildren="MCP" />
              </Form.Item>
              <Form.Item name="allow_tasks" valuePropName="checked">
                <Switch checkedChildren="Tasks" unCheckedChildren="Tasks" />
              </Form.Item>
              <Form.Item name="advanced_config_enabled" valuePropName="checked">
                <Switch checkedChildren="Advanced" unCheckedChildren="Advanced" />
              </Form.Item>
            </Space>
            <Space direction="vertical" size="small" style={{ width: "100%" }}>
              {policyDeleteReason ? (
                <Text type="secondary">{policyDeleteReason}</Text>
              ) : null}
              <Space>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={saving}
                  disabled={!selectedPolicy}
                >
                  保存策略
                </Button>
                <Button
                  danger
                  onClick={() => void handleDeletePolicy()}
                  disabled={!selectedPolicy || Boolean(policyDeleteReason)}
                  loading={saving}
                >
                  删除策略
                </Button>
              </Space>
            </Space>
          </Form>
        </Card>
      </Col>
    </Row>
  )

  const templateTab = (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={9}>
        <Card
          title="模板列表"
          loading={loading}
          extra={<Button onClick={startNewTemplate}>新建模板</Button>}
        >
          <List
            dataSource={templates}
            locale={{ emptyText: "暂无模板" }}
            renderItem={(template) => (
              <List.Item>
                <Button
                  type="text"
                  style={{
                    paddingInline: 0,
                    textAlign: "left",
                    width: "100%",
                    height: "auto",
                  }}
                  onClick={() => selectTemplate(template.template_id)}
                >
                  <Space direction="vertical" size={0}>
                    <Text strong>{template.display_name}</Text>
                    <Text type="secondary">{template.template_id}</Text>
                  </Space>
                </Button>
              </List.Item>
            )}
          />
        </Card>
      </Col>
      <Col xs={24} xl={15}>
        <Card title="模板详情" loading={loading}>
          <Form<TemplateFormValues>
            key={selectedTemplate?.template_id ?? "empty-template"}
            initialValues={
              selectedTemplate ? templateToForm(selectedTemplate) : undefined
            }
            layout="vertical"
            name="templateConfig"
            onFinish={handleSaveTemplate}
          >
            <Row gutter={12}>
              <Col xs={24} md={12}>
                <Form.Item
                  label="模板 ID"
                  name="template_id"
                  rules={[{ required: true, message: "请输入模板 ID" }]}
                >
                  <Input aria-label="模板 ID" disabled={!isTemplateIdEditable} />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item
                  label="模板名称"
                  name="display_name"
                  rules={[{ required: true, message: "请输入模板名称" }]}
                >
                  <Input aria-label="模板名称" />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item label="默认模型" name="default_model">
                  <Input aria-label="默认模型" />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item label="默认 Prompt Files" name="default_prompt_files_text">
                  <Input placeholder="AGENTS.md, system.md" />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item label="默认 Skills" name="default_skills_text">
                  <Input aria-label="默认 Skills" placeholder="sales_report" />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item label="默认 Tools" name="default_tools_text">
                  <Input placeholder="read_file, search" />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item label="默认任务模板 JSON" name="default_task_templates_text">
              <TextArea
                aria-label="默认任务模板 JSON"
                rows={8}
                placeholder='[{"name":"日报"}]'
              />
            </Form.Item>
            {templateError ? <Alert type="error" showIcon message={templateError} /> : null}
            <Space direction="vertical" size="small" style={{ width: "100%" }}>
              {templateDeleteReason ? (
                <Text type="secondary">{templateDeleteReason}</Text>
              ) : null}
              <Space>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={saving}
                  disabled={!selectedTemplate}
                >
                  保存模板
                </Button>
                <Button
                  danger
                  onClick={() => void handleDeleteTemplate()}
                  disabled={!selectedTemplate || Boolean(templateDeleteReason)}
                  loading={saving}
                >
                  删除模板
                </Button>
              </Space>
            </Space>
          </Form>
        </Card>
      </Col>
    </Row>
  )

  const tabItems = [
    { key: "policies", label: "平台策略", children: policyTab, forceRender: true },
    { key: "templates", label: "租户模板", children: templateTab, forceRender: true },
  ]

  const selectedReferences =
    activeTab === "templates" ? templateReferences : policyReferences

  return (
    <div className="enterprise-page">
      {contextHolder}
      <Space direction="vertical" size="large" style={{ width: "100%" }}>
        <div>
          <Title level={3} style={{ margin: 0 }}>
            策略配置
          </Title>
          <Text type="secondary">平台策略、租户模板与影响范围</Text>
        </div>

        <PageCompletenessPanel pageKey="policies" compact />

        <Alert
          type="info"
          showIcon
          message="策略变更为平台级配置"
          description="当前提供策略与模板 CRUD、引用影响预览和受保护删除；发布审批、版本回滚和批量应用仍为阶段化能力。"
        />

        <Row gutter={[16, 16]}>
          <Col xs={24} md={12} xl={6}>
            <Card>
              <Statistic title="策略数" value={policies.length} />
            </Card>
          </Col>
          <Col xs={24} md={12} xl={6}>
            <Card>
              <Statistic title="模板数" value={templates.length} />
            </Card>
          </Col>
          <Col xs={24} md={12} xl={6}>
            <Card>
              <Statistic title="被引用项" value={referencedItemCount} />
            </Card>
          </Col>
          <Col xs={24} md={12} xl={6}>
            <Card>
              <Statistic title="可删除项" value={deletableItemCount} />
            </Card>
          </Col>
        </Row>

        <Card title="影响租户" loading={loading}>
          <List
            dataSource={selectedReferences}
            locale={{ emptyText: "暂无受影响租户" }}
            renderItem={(tenant) => (
              <List.Item>
                <Space direction="vertical" size={0}>
                  <Space wrap>
                    <Text strong>{tenant.display_name}</Text>
                    <Tag>{tenant.status}</Tag>
                  </Space>
                  <Text type="secondary">
                    {tenant.tenant_id} / {tenant.agent_id} · 策略 {tenant.policy_id} · 模板 {tenant.template_id}
                  </Text>
                </Space>
              </List.Item>
            )}
          />
        </Card>

        <Tabs
          activeKey={activeTab}
          items={tabItems}
          onChange={setActiveTab}
        />
      </Space>
    </div>
  )
}

export default PoliciesPage
