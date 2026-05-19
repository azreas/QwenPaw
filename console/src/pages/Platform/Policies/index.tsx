import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Button,
  Card,
  Col,
  Divider,
  Empty,
  Form,
  Input,
  InputNumber,
  Popconfirm,
  Row,
  Select,
  Space,
  Switch,
  Table,
  Tabs,
  Tag,
  Typography,
  type SelectProps,
  type TableColumnsType,
} from "antd";
import {
  DeleteOutlined,
  PlusOutlined,
  ReloadOutlined,
  SaveOutlined,
} from "@ant-design/icons";
import { PageHeader } from "@/components/PageHeader";
import { platformTenancyApi } from "../../../api/modules/platformTenancy";
import { providerApi } from "../../../api/modules/provider";
import { toolsApi } from "../../../api/modules/tools";
import type { ModelInfo, ProviderInfo } from "../../../api/types";
import type {
  TenantPolicy,
  TenantTemplate,
} from "../../../api/types/platformTenancy";
import { useAppMessage } from "../../../hooks/useAppMessage";
import {
  formToPolicy,
  policyToForm,
  type PolicyFormValues,
} from "./policyForm";
import styles from "./index.module.less";

type TemplateFormValues = Omit<TenantTemplate, "default_task_templates"> & {
  default_task_templates_json: string;
};
type SelectOptions = NonNullable<SelectProps["options"]>;

const mcpTransportOptions = [
  { label: "stdio", value: "stdio" },
  { label: "streamable_http", value: "streamable_http" },
  { label: "sse", value: "sse" },
];

function renderSwitchTag(enabled: boolean) {
  return enabled ? <Tag color="green">ON</Tag> : <Tag>OFF</Tag>;
}

function uniqueId(prefix: string): string {
  return `${prefix}_${Date.now().toString(36)}`;
}

function createDraftPolicy(): TenantPolicy {
  return {
    policy_id: uniqueId("policy"),
    display_name: "新建成员策略",
    allow_model_switch: true,
    allowed_models: [],
    allow_skill_create: true,
    allow_skill_upload_zip: true,
    allow_skill_hub_import: true,
    allow_tools: true,
    allowed_tools: [],
    allow_mcp: true,
    allowed_mcp_transports: ["sse", "streamable_http"],
    allow_tasks: true,
    max_cron_jobs: 20,
    min_cron_interval_minutes: 5,
    allow_task_run_now: true,
    allow_task_tools: true,
    task_timeout_seconds: 120,
    file_upload_limit_mb: 100,
    token_quota_monthly: null,
    advanced_config_enabled: false,
  };
}

function createDraftTemplate(): TenantTemplate {
  return {
    template_id: uniqueId("template"),
    display_name: "新建成员模板",
    default_model: null,
    default_prompt_files: [],
    default_skills: [],
    default_tools: [],
    default_task_templates: [],
  };
}

function templateToForm(template: TenantTemplate): TemplateFormValues {
  return {
    template_id: template.template_id,
    display_name: template.display_name,
    default_model: template.default_model,
    default_prompt_files: [...template.default_prompt_files],
    default_skills: [...template.default_skills],
    default_tools: [...template.default_tools],
    default_task_templates_json: JSON.stringify(
      template.default_task_templates,
      null,
      2,
    ),
  };
}

function normalizeStringList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => String(item).trim())
    .filter((item) => item.length > 0);
}

function normalizeList<T>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : [];
}

function formToTemplate(
  values: Partial<TemplateFormValues>,
  previousTemplate: TenantTemplate,
): TenantTemplate {
  const rawTaskTemplates = values.default_task_templates_json?.trim() || "[]";
  const parsedTaskTemplates = JSON.parse(rawTaskTemplates);
  if (!Array.isArray(parsedTaskTemplates)) {
    throw new Error("默认任务模板 JSON 必须是数组");
  }

  return {
    template_id: values.template_id?.trim() || previousTemplate.template_id,
    display_name: values.display_name?.trim() || previousTemplate.display_name,
    default_model: values.default_model?.trim() || null,
    default_prompt_files: normalizeStringList(
      values.default_prompt_files ?? previousTemplate.default_prompt_files,
    ),
    default_skills: normalizeStringList(
      values.default_skills ?? previousTemplate.default_skills,
    ),
    default_tools: normalizeStringList(
      values.default_tools ?? previousTemplate.default_tools,
    ),
    default_task_templates: parsedTaskTemplates,
  };
}

function buildModelOptions(providers: unknown): SelectOptions {
  const options = new Map<string, string>();
  for (const provider of normalizeList<ProviderInfo>(providers)) {
    const models = [
      ...normalizeList<ModelInfo>(provider.models),
      ...normalizeList<ModelInfo>(provider.extra_models),
    ];
    for (const model of models) {
      options.set(model.id, `${provider.name} / ${model.name || model.id}`);
    }
  }

  return Array.from(options.entries()).map(([value, label]) => ({
    label,
    value,
  }));
}

export default function PlatformPoliciesPage() {
  const { t } = useTranslation();
  const { message } = useAppMessage();
  const [policyForm] = Form.useForm<PolicyFormValues>();
  const [templateForm] = Form.useForm<TemplateFormValues>();
  const [activeTab, setActiveTab] = useState("policies");
  const [policies, setPolicies] = useState<TenantPolicy[]>([]);
  const [templates, setTemplates] = useState<TenantTemplate[]>([]);
  const [selectedPolicyId, setSelectedPolicyId] = useState<string>("");
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>("");
  const [draftPolicyIds, setDraftPolicyIds] = useState<string[]>([]);
  const [draftTemplateIds, setDraftTemplateIds] = useState<string[]>([]);
  const [modelOptions, setModelOptions] = useState<SelectOptions>([]);
  const [toolOptions, setToolOptions] = useState<SelectOptions>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const selectedPolicy = useMemo(
    () => policies.find((policy) => policy.policy_id === selectedPolicyId) ?? null,
    [policies, selectedPolicyId],
  );

  const selectedTemplate = useMemo(
    () =>
      templates.find((template) => template.template_id === selectedTemplateId) ??
      null,
    [templates, selectedTemplateId],
  );

  const isDraftPolicy = selectedPolicy
    ? draftPolicyIds.includes(selectedPolicy.policy_id)
    : false;
  const isDraftTemplate = selectedTemplate
    ? draftTemplateIds.includes(selectedTemplate.template_id)
    : false;

  const loadData = async () => {
    setLoading(true);
    try {
      const [policyResponse, templateResponse, providers, tools] =
        await Promise.all([
          platformTenancyApi.listPolicies(),
          platformTenancyApi.listTemplates(),
          providerApi.listProviders(),
          toolsApi.listTools(),
        ]);
      const nextPolicies = normalizeList<TenantPolicy>(policyResponse.policies);
      const nextTemplates = normalizeList<TenantTemplate>(
        templateResponse.templates,
      );
      setPolicies(nextPolicies);
      setTemplates(nextTemplates);
      setModelOptions(buildModelOptions(providers));
      setToolOptions(
        normalizeList<(typeof tools)[number]>(tools).map((tool) => ({
          label: tool.enabled ? tool.name : `${tool.name} (disabled)`,
          value: tool.name,
          disabled: !tool.enabled,
        })),
      );
      setDraftPolicyIds([]);
      setDraftTemplateIds([]);
      setSelectedPolicyId((current) =>
        nextPolicies.some((policy) => policy.policy_id === current)
          ? current
          : nextPolicies[0]?.policy_id ?? "",
      );
      setSelectedTemplateId((current) =>
        nextTemplates.some(
          (template) => template.template_id === current,
        )
          ? current
          : nextTemplates[0]?.template_id ?? "",
      );
    } catch (error) {
      console.error("Failed to load platform policies and templates:", error);
      message.error(t("platformPolicies.loadFailed", "加载模板与策略失败"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, []);

  useEffect(() => {
    if (selectedPolicy) {
      policyForm.setFieldsValue(policyToForm(selectedPolicy));
    } else {
      policyForm.resetFields();
    }
  }, [policyForm, selectedPolicy]);

  useEffect(() => {
    if (selectedTemplate) {
      templateForm.setFieldsValue(templateToForm(selectedTemplate));
    } else {
      templateForm.resetFields();
    }
  }, [templateForm, selectedTemplate]);

  const handleCreatePolicy = () => {
    const draft = createDraftPolicy();
    setPolicies((current) => [...current, draft]);
    setDraftPolicyIds((current) => [...current, draft.policy_id]);
    setSelectedPolicyId(draft.policy_id);
    setActiveTab("policies");
  };

  const handleCreateTemplate = () => {
    const draft = createDraftTemplate();
    setTemplates((current) => [...current, draft]);
    setDraftTemplateIds((current) => [...current, draft.template_id]);
    setSelectedTemplateId(draft.template_id);
    setActiveTab("templates");
  };

  const handleSavePolicy = async () => {
    if (!selectedPolicy) return;

    setSaving(true);
    try {
      const values = await policyForm.validateFields();
      const payload = formToPolicy(values, selectedPolicy);
      const duplicate = policies.some(
        (policy) =>
          policy.policy_id === payload.policy_id &&
          policy.policy_id !== selectedPolicy.policy_id,
      );
      if (duplicate) {
        message.error(t("platformPolicies.duplicatePolicy", "策略 ID 已存在"));
        return;
      }

      const savedPolicy = await platformTenancyApi.savePolicy(payload);
      setPolicies((current) =>
        current.map((policy) =>
          policy.policy_id === selectedPolicy.policy_id ? savedPolicy : policy,
        ),
      );
      setDraftPolicyIds((current) =>
        current.filter((policyId) => policyId !== selectedPolicy.policy_id),
      );
      setSelectedPolicyId(savedPolicy.policy_id);
      policyForm.setFieldsValue(policyToForm(savedPolicy));
      message.success(t("platformPolicies.saveSuccess", "策略已保存"));
    } catch (error) {
      console.error("Failed to save platform policy:", error);
      const fallback = t("platformPolicies.saveFailed", "保存策略失败");
      message.error(error instanceof Error ? error.message : fallback);
    } finally {
      setSaving(false);
    }
  };

  const handleSaveTemplate = async () => {
    if (!selectedTemplate) return;

    setSaving(true);
    try {
      const values = await templateForm.validateFields();
      const payload = formToTemplate(values, selectedTemplate);
      const duplicate = templates.some(
        (template) =>
          template.template_id === payload.template_id &&
          template.template_id !== selectedTemplate.template_id,
      );
      if (duplicate) {
        message.error(t("platformPolicies.duplicateTemplate", "模板 ID 已存在"));
        return;
      }

      const savedTemplate = await platformTenancyApi.saveTemplate(payload);
      setTemplates((current) =>
        current.map((template) =>
          template.template_id === selectedTemplate.template_id
            ? savedTemplate
            : template,
        ),
      );
      setDraftTemplateIds((current) =>
        current.filter(
          (templateId) => templateId !== selectedTemplate.template_id,
        ),
      );
      setSelectedTemplateId(savedTemplate.template_id);
      templateForm.setFieldsValue(templateToForm(savedTemplate));
      message.success(t("platformPolicies.templateSaveSuccess", "模板已保存"));
    } catch (error) {
      console.error("Failed to save platform template:", error);
      const fallback = t("platformPolicies.templateSaveFailed", "保存模板失败");
      message.error(error instanceof Error ? error.message : fallback);
    } finally {
      setSaving(false);
    }
  };

  const handleDeletePolicy = async () => {
    if (!selectedPolicy) return;

    if (isDraftPolicy) {
      setPolicies((current) =>
        current.filter((policy) => policy.policy_id !== selectedPolicy.policy_id),
      );
      setDraftPolicyIds((current) =>
        current.filter((policyId) => policyId !== selectedPolicy.policy_id),
      );
      setSelectedPolicyId(policies[0]?.policy_id ?? "");
      return;
    }

    setSaving(true);
    try {
      await platformTenancyApi.deletePolicy(selectedPolicy.policy_id);
      const nextPolicies = policies.filter(
        (policy) => policy.policy_id !== selectedPolicy.policy_id,
      );
      setPolicies(nextPolicies);
      setSelectedPolicyId(nextPolicies[0]?.policy_id ?? "");
      message.success(t("platformPolicies.deleteSuccess", "策略已删除"));
    } catch (error) {
      console.error("Failed to delete platform policy:", error);
      const fallback = t("platformPolicies.deleteFailed", "删除策略失败");
      message.error(error instanceof Error ? error.message : fallback);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteTemplate = async () => {
    if (!selectedTemplate) return;

    if (isDraftTemplate) {
      setTemplates((current) =>
        current.filter(
          (template) => template.template_id !== selectedTemplate.template_id,
        ),
      );
      setDraftTemplateIds((current) =>
        current.filter(
          (templateId) => templateId !== selectedTemplate.template_id,
        ),
      );
      setSelectedTemplateId(templates[0]?.template_id ?? "");
      return;
    }

    setSaving(true);
    try {
      await platformTenancyApi.deleteTemplate(selectedTemplate.template_id);
      const nextTemplates = templates.filter(
        (template) => template.template_id !== selectedTemplate.template_id,
      );
      setTemplates(nextTemplates);
      setSelectedTemplateId(nextTemplates[0]?.template_id ?? "");
      message.success(t("platformPolicies.templateDeleteSuccess", "模板已删除"));
    } catch (error) {
      console.error("Failed to delete platform template:", error);
      const fallback = t("platformPolicies.templateDeleteFailed", "删除模板失败");
      message.error(error instanceof Error ? error.message : fallback);
    } finally {
      setSaving(false);
    }
  };

  const policyColumns: TableColumnsType<TenantPolicy> = [
    {
      title: t("platformPolicies.table.policy", "策略"),
      dataIndex: "display_name",
      render: (value: string, policy) => (
        <Space direction="vertical" size={0}>
          <Typography.Text strong>{value || policy.policy_id}</Typography.Text>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            {policy.policy_id}
          </Typography.Text>
        </Space>
      ),
    },
    {
      title: "MCP",
      dataIndex: "allow_mcp",
      width: 84,
      render: renderSwitchTag,
    },
    {
      title: t("platformPolicies.table.tasks", "任务"),
      dataIndex: "allow_tasks",
      width: 84,
      render: renderSwitchTag,
    },
    {
      title: t("platformPolicies.table.cronLimit", "Cron 上限"),
      dataIndex: "max_cron_jobs",
      width: 110,
    },
  ];

  const templateColumns: TableColumnsType<TenantTemplate> = [
    {
      title: t("platformPolicies.table.template", "模板"),
      dataIndex: "display_name",
      render: (value: string, template) => (
        <Space direction="vertical" size={0}>
          <Typography.Text strong>
            {value || template.template_id}
          </Typography.Text>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            {template.template_id}
          </Typography.Text>
        </Space>
      ),
    },
    {
      title: t("platformPolicies.table.defaultModel", "默认模型"),
      dataIndex: "default_model",
      render: (value: string | null) => value || "-",
    },
    {
      title: t("platformPolicies.table.defaultTools", "工具"),
      dataIndex: "default_tools",
      width: 90,
      render: (value: string[]) => value.length,
    },
  ];

  const activeSave =
    activeTab === "policies" ? handleSavePolicy : handleSaveTemplate;
  const activeDelete =
    activeTab === "policies" ? handleDeletePolicy : handleDeleteTemplate;
  const activeCreate =
    activeTab === "policies" ? handleCreatePolicy : handleCreateTemplate;
  const canSave =
    activeTab === "policies" ? Boolean(selectedPolicy) : Boolean(selectedTemplate);
  const canDelete =
    activeTab === "policies"
      ? Boolean(selectedPolicy && selectedPolicy.policy_id !== "default")
      : Boolean(selectedTemplate && selectedTemplate.template_id !== "default");

  const policyPanel = (
    <div className={styles.workspaceGrid}>
      <div className={styles.listPane}>
        <Card
          className={styles.listCard}
          title={t("platformPolicies.table.title", "策略列表")}
          styles={{ body: { padding: 0 } }}
        >
          <Table<TenantPolicy>
            rowKey="policy_id"
            columns={policyColumns}
            dataSource={policies}
            loading={loading}
            pagination={false}
            rowSelection={{
              type: "radio",
              selectedRowKeys: selectedPolicyId ? [selectedPolicyId] : [],
              onChange: (keys) => setSelectedPolicyId(String(keys[0] ?? "")),
            }}
            onRow={(record) => ({
              onClick: () => setSelectedPolicyId(record.policy_id),
            })}
            scroll={{ x: 480 }}
          />
        </Card>
      </div>

      <div className={styles.editorPane}>
        <Card
          className={styles.editorCard}
          title={t("platformPolicies.editor.title", "策略配置")}
        >
          {!selectedPolicy ? (
            <Empty description={t("platformPolicies.empty", "暂无策略")} />
          ) : (
            <Form<PolicyFormValues>
              form={policyForm}
              layout="vertical"
              disabled={saving}
            >
              <Row gutter={16}>
                <Col xs={24} md={12}>
                  <Form.Item
                    name="policy_id"
                    label={t("platformPolicies.fields.policyId", "策略 ID")}
                    rules={[{ required: true }]}
                  >
                    <Input disabled={!isDraftPolicy} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item
                    name="display_name"
                    label={t("platformPolicies.fields.displayName", "显示名称")}
                    rules={[{ required: true }]}
                  >
                    <Input />
                  </Form.Item>
                </Col>
              </Row>

              <Divider orientation="left">
                {t("platformPolicies.sections.modelsAndTools", "模型与工具")}
              </Divider>
              <Row gutter={16}>
                <Col xs={24} md={8}>
                  <Form.Item
                    name="allow_model_switch"
                    label={t("platformPolicies.fields.allowModelSwitch", "允许切换模型")}
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item
                    name="allow_tools"
                    label={t("platformPolicies.fields.allowTools", "启用工具")}
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item
                    name="allow_task_tools"
                    label={t("platformPolicies.fields.allowTaskTools", "任务可用工具")}
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>
                </Col>
              </Row>
              <Form.Item
                name="allowed_models"
                label={t("platformPolicies.fields.allowedModels", "允许模型")}
                extra={
                  modelOptions.length === 0
                    ? t(
                        "platformPolicies.fields.allowedModelsEmpty",
                        "当前没有可选模型。请先到模型页为供应商配置模型，或直接输入模型 ID。",
                      )
                    : null
                }
              >
                <Select
                  mode="tags"
                  options={modelOptions}
                  placeholder={t(
                    "platformPolicies.fields.allowedModelsPlaceholder",
                    "选择或输入允许的模型",
                  )}
                  showSearch
                  optionFilterProp="label"
                  tokenSeparators={[","]}
                  notFoundContent={t(
                    "platformPolicies.fields.allowedModelsNotFound",
                    "暂无可选模型",
                  )}
                />
              </Form.Item>
              <Form.Item
                name="allowed_tools"
                label={t("platformPolicies.fields.allowedTools", "允许工具")}
                extra={
                  toolOptions.length === 0
                    ? t(
                        "platformPolicies.fields.allowedToolsEmpty",
                        "当前没有可选工具。可直接输入工具名，或确认后端工具清单已加载。",
                      )
                    : null
                }
              >
                <Select
                  mode="tags"
                  options={toolOptions}
                  placeholder={t(
                    "platformPolicies.fields.allowedToolsPlaceholder",
                    "选择或输入允许的工具",
                  )}
                  showSearch
                  optionFilterProp="label"
                  tokenSeparators={[","]}
                  notFoundContent={t(
                    "platformPolicies.fields.allowedToolsNotFound",
                    "暂无可选工具",
                  )}
                />
              </Form.Item>

              <Divider orientation="left">MCP</Divider>
              <Row gutter={16}>
                <Col xs={24} md={8}>
                  <Form.Item
                    name="allow_mcp"
                    label={t("platformPolicies.fields.allowMcp", "启用 MCP")}
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>
                </Col>
                <Col xs={24} md={16}>
                  <Form.Item
                    name="allowed_mcp_transports"
                    label={t("platformPolicies.fields.allowedMcpTransports", "允许传输")}
                  >
                    <Select
                      mode="tags"
                      options={mcpTransportOptions}
                      tokenSeparators={[","]}
                    />
                  </Form.Item>
                </Col>
              </Row>

              <Divider orientation="left">
                {t("platformPolicies.sections.tasks", "任务")}
              </Divider>
              <Row gutter={16}>
                <Col xs={24} md={8}>
                  <Form.Item
                    name="allow_tasks"
                    label={t("platformPolicies.fields.allowTasks", "启用任务")}
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item
                    name="allow_task_run_now"
                    label={t("platformPolicies.fields.allowTaskRunNow", "允许立即运行")}
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item
                    name="max_cron_jobs"
                    label={t("platformPolicies.fields.maxCronJobs", "Cron 上限")}
                    rules={[{ required: true }]}
                  >
                    <InputNumber min={0} style={{ width: "100%" }} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item
                    name="min_cron_interval_minutes"
                    label={t("platformPolicies.fields.minCronInterval", "最小间隔（分钟）")}
                    rules={[{ required: true }]}
                  >
                    <InputNumber min={1} style={{ width: "100%" }} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item
                    name="task_timeout_seconds"
                    label={t("platformPolicies.fields.taskTimeout", "任务超时（秒）")}
                    rules={[{ required: true }]}
                  >
                    <InputNumber min={1} style={{ width: "100%" }} />
                  </Form.Item>
                </Col>
              </Row>

              <Divider orientation="left">
                {t("platformPolicies.sections.skillsAndAdvanced", "技能与高级配置")}
              </Divider>
              <Row gutter={16}>
                <Col xs={24} md={8}>
                  <Form.Item
                    name="allow_skill_create"
                    label={t("platformPolicies.fields.allowSkillCreate", "允许创建技能")}
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item
                    name="allow_skill_upload_zip"
                    label={t("platformPolicies.fields.allowSkillUploadZip", "允许上传 ZIP")}
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item
                    name="allow_skill_hub_import"
                    label={t("platformPolicies.fields.allowSkillHubImport", "允许从技能池导入")}
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item
                    name="file_upload_limit_mb"
                    label={t("platformPolicies.fields.fileUploadLimit", "文件上传上限（MB）")}
                    rules={[{ required: true }]}
                  >
                    <InputNumber min={1} style={{ width: "100%" }} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item
                    name="token_quota_monthly"
                    label={t("platformPolicies.fields.tokenQuotaMonthly", "月 Token 配额")}
                  >
                    <InputNumber min={0} style={{ width: "100%" }} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item
                    name="advanced_config_enabled"
                    label={t("platformPolicies.fields.advancedConfig", "WebChat 高级配置")}
                    valuePropName="checked"
                    extra={t(
                      "platformPolicies.fields.advancedConfigHelp",
                      "开启后，普通成员可在 WebChat 进入 Agent 高级配置页；关闭时只保留聊天、任务、用量等成员工作台入口。",
                    )}
                  >
                    <Switch />
                  </Form.Item>
                </Col>
              </Row>
            </Form>
          )}
        </Card>
      </div>
    </div>
  );

  const templatePanel = (
    <div className={styles.workspaceGrid}>
      <div className={styles.listPane}>
        <Card
          className={styles.listCard}
          title={t("platformPolicies.templateTable.title", "模板列表")}
          styles={{ body: { padding: 0 } }}
        >
          <Table<TenantTemplate>
            rowKey="template_id"
            columns={templateColumns}
            dataSource={templates}
            loading={loading}
            pagination={false}
            rowSelection={{
              type: "radio",
              selectedRowKeys: selectedTemplateId ? [selectedTemplateId] : [],
              onChange: (keys) => setSelectedTemplateId(String(keys[0] ?? "")),
            }}
            onRow={(record) => ({
              onClick: () => setSelectedTemplateId(record.template_id),
            })}
            scroll={{ x: 460 }}
          />
        </Card>
      </div>

      <div className={styles.editorPane}>
        <Card
          className={styles.editorCard}
          title={t("platformPolicies.templateEditor.title", "模板配置")}
        >
          {!selectedTemplate ? (
            <Empty description={t("platformPolicies.noTemplate", "暂无模板")} />
          ) : (
            <Form<TemplateFormValues>
              form={templateForm}
              layout="vertical"
              disabled={saving}
            >
              <Row gutter={16}>
                <Col xs={24} md={12}>
                  <Form.Item
                    name="template_id"
                    label={t("platformPolicies.fields.templateId", "模板 ID")}
                    rules={[{ required: true }]}
                  >
                    <Input disabled={!isDraftTemplate} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item
                    name="display_name"
                    label={t("platformPolicies.fields.displayName", "显示名称")}
                    rules={[{ required: true }]}
                  >
                    <Input />
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item
                name="default_model"
                label={t("platformPolicies.fields.defaultModel", "默认模型")}
              >
                <Select
                  allowClear
                  showSearch
                  options={modelOptions}
                  optionFilterProp="label"
                  placeholder={t(
                    "platformPolicies.fields.defaultModelPlaceholder",
                    "从模型列表选择默认模型",
                  )}
                  notFoundContent={t(
                    "platformPolicies.fields.defaultModelNotFound",
                    "暂无可选模型",
                  )}
                />
              </Form.Item>
              <Form.Item
                name="default_tools"
                label={t("platformPolicies.fields.defaultTools", "默认工具")}
              >
                <Select
                  mode="tags"
                  options={toolOptions}
                  placeholder={t(
                    "platformPolicies.fields.defaultToolsPlaceholder",
                    "选择或输入默认工具",
                  )}
                  showSearch
                  optionFilterProp="label"
                  tokenSeparators={[","]}
                  notFoundContent={t(
                    "platformPolicies.fields.defaultToolsNotFound",
                    "暂无可选工具",
                  )}
                />
              </Form.Item>
              <Form.Item
                name="default_skills"
                label={t("platformPolicies.fields.defaultSkills", "默认技能")}
              >
                <Select
                  mode="tags"
                  tokenSeparators={[","]}
                  placeholder={t(
                    "platformPolicies.fields.defaultSkillsPlaceholder",
                    "输入或粘贴默认技能",
                  )}
                />
              </Form.Item>
              <Form.Item
                name="default_prompt_files"
                label={t("platformPolicies.fields.defaultPromptFiles", "默认提示词文件")}
              >
                <Select
                  mode="tags"
                  tokenSeparators={[","]}
                  placeholder={t(
                    "platformPolicies.fields.defaultPromptFilesPlaceholder",
                    "输入或粘贴提示词文件名",
                  )}
                />
              </Form.Item>
              <Form.Item
                name="default_task_templates_json"
                label={t("platformPolicies.fields.defaultTaskTemplates", "默认任务模板 JSON")}
                extra={t(
                  "platformPolicies.fields.defaultTaskTemplatesHelp",
                  "用于后续按模板初始化成员任务，必须是 JSON 数组；暂时可保持为空数组。",
                )}
                rules={[{ required: true }]}
              >
                <Input.TextArea autoSize={{ minRows: 4, maxRows: 8 }} />
              </Form.Item>
            </Form>
          )}
        </Card>
      </div>
    </div>
  );

  return (
    <div className={styles.page}>
      <PageHeader
        className={styles.pageHeader}
        parent={t("nav.platformOps")}
        current={t("nav.platformPolicies")}
        subRow={
          <Typography.Text type="secondary" style={{ fontSize: 13 }}>
            {t(
              "platformPolicies.subtitle",
              "策略定义成员权限边界，模板定义成员的默认初始内容；两者共同决定新租户的起点。",
            )}
          </Typography.Text>
        }
        extra={
          <Space wrap className={styles.headerActions}>
            <Button icon={<ReloadOutlined />} onClick={loadData} loading={loading}>
              {t("common.refresh", "刷新")}
            </Button>
            <Button icon={<PlusOutlined />} onClick={activeCreate}>
              {activeTab === "policies"
                ? t("platformPolicies.createPolicy", "新增策略")
                : t("platformPolicies.createTemplate", "新增模板")}
            </Button>
            <Popconfirm
              title={
                activeTab === "policies"
                  ? t("platformPolicies.deleteConfirm", "删除当前策略？")
                  : t("platformPolicies.templateDeleteConfirm", "删除当前模板？")
              }
              onConfirm={activeDelete}
              disabled={!canDelete || saving}
            >
              <Button
                danger
                icon={<DeleteOutlined />}
                disabled={!canDelete || saving}
              >
                {t("common.delete", "删除")}
              </Button>
            </Popconfirm>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={activeSave}
              loading={saving}
              disabled={!canSave}
            >
              {t("common.save", "保存")}
            </Button>
          </Space>
        }
      />

      <Tabs
        className={styles.tabs}
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: "policies",
            label: t("platformPolicies.tabs.policies", "策略"),
            children: policyPanel,
          },
          {
            key: "templates",
            label: t("platformPolicies.tabs.templates", "模板"),
            children: templatePanel,
          },
        ]}
      />
    </div>
  );
}
