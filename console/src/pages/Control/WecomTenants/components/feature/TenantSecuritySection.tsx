import { useEffect, useMemo, useState } from "react";
import { Alert } from "@agentscope-ai/design";
import { Button, Card, Form, Input, Modal, Select, Table } from "@agentscope-ai/design";
import type { ColumnsType } from "antd/es/table";
import { useTranslation } from "react-i18next";
import type {
  WecomTenantSecurityRule,
  WecomTenantSecuritySettings,
} from "../../../../../api/types";
import { useAppMessage } from "../../../../../hooks/useAppMessage";
import styles from "../../index.module.less";

interface Props {
  value: WecomTenantSecuritySettings;
  loading: boolean;
  saving: boolean;
  onChange: (value: WecomTenantSecuritySettings) => void;
  onSave: (value: WecomTenantSecuritySettings) => Promise<void>;
}

interface RuleFormValues {
  id: string;
  toolsText: string;
  severity: string;
  conditionsJson: string;
}

function prettyJson(value: unknown): string {
  return JSON.stringify(value ?? {}, null, 2);
}

function splitList(value: string): string[] {
  return value
    .split(/[,\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function restRule(rule: WecomTenantSecurityRule) {
  const { id, tools, severity, ...rest } = rule;
  return rest;
}

export function TenantSecuritySection({
  value,
  loading,
  saving,
  onChange,
  onSave,
}: Props) {
  const { t } = useTranslation();
  const { message } = useAppMessage();
  const [form] = Form.useForm<RuleFormValues>();
  const [ruleModalOpen, setRuleModalOpen] = useState(false);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [advancedJson, setAdvancedJson] = useState(prettyJson(value));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setAdvancedJson(prettyJson(value));
    setError(null);
  }, [value]);

  const openRuleModal = (rule?: WecomTenantSecurityRule, index?: number) => {
    setEditingIndex(index ?? null);
    form.setFieldsValue({
      id: rule?.id || "",
      toolsText: (rule?.tools || []).join("\n"),
      severity: rule?.severity || "HIGH",
      conditionsJson: prettyJson(restRule(rule || {})),
    });
    setRuleModalOpen(true);
  };

  const saveRule = async () => {
    const fields = await form.validateFields();
    let conditions: Record<string, unknown>;
    try {
      conditions = JSON.parse(fields.conditionsJson || "{}") as Record<
        string,
        unknown
      >;
    } catch (err) {
      setError((err as Error).message);
      return;
    }
    const nextRule: WecomTenantSecurityRule = {
      ...conditions,
      id: fields.id.trim() || `custom_${Date.now()}`,
      tools: splitList(fields.toolsText),
      severity: fields.severity,
    };
    const rules = [...(value.tool_guard_rules || [])];
    if (editingIndex === null) {
      rules.push(nextRule);
    } else {
      rules[editingIndex] = nextRule;
    }
    onChange({ ...value, tool_guard_rules: rules });
    setRuleModalOpen(false);
    setError(null);
  };

  const deleteRule = (index: number) => {
    const nextRules = value.tool_guard_rules.filter((_, itemIndex) => itemIndex !== index);
    onChange({ ...value, tool_guard_rules: nextRules });
  };

  const applyAdvancedJson = () => {
    try {
      const parsed = JSON.parse(advancedJson) as WecomTenantSecuritySettings;
      onChange({
        approval_level: parsed.approval_level || "AUTO",
        tool_guard_rules: Array.isArray(parsed.tool_guard_rules)
          ? parsed.tool_guard_rules
          : [],
      });
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const saveSecurity = async () => {
    try {
      JSON.parse(advancedJson);
    } catch (err) {
      setError((err as Error).message);
      return;
    }
    await onSave(value);
    message.success(t("wecomTenants.configSavedReloaded"));
  };

  const columns: ColumnsType<WecomTenantSecurityRule> = useMemo(
    () => [
      {
        title: t("wecomTenants.ruleName"),
        key: "id",
        render: (_, rule) => rule.id || "-",
      },
      {
        title: t("wecomTenants.ruleTools"),
        key: "tools",
        render: (_, rule) => (rule.tools || []).join(", ") || "-",
      },
      {
        title: t("wecomTenants.ruleAction"),
        key: "severity",
        render: (_, rule) => rule.severity || "HIGH",
      },
      {
        title: t("wecomTenants.actions"),
        key: "actions",
        width: 140,
        render: (_, rule, index) => (
          <div className={styles.rowActions}>
            <Button size="small" onClick={() => openRuleModal(rule, index)}>
              {t("common.edit")}
            </Button>
            <Button size="small" danger onClick={() => deleteRule(index)}>
              {t("common.delete")}
            </Button>
          </div>
        ),
      },
    ],
    [t],
  );

  return (
    <Card title={t("wecomTenants.security")} loading={loading}>
      <div className={styles.stack}>
        {error && (
          <Alert
            type="error"
            showIcon
            message={t("wecomTenants.configError")}
            description={error}
          />
        )}
        <div className={styles.formGrid}>
          <Select
            value={value.approval_level || "AUTO"}
            onChange={(approvalLevel) =>
              onChange({ ...value, approval_level: approvalLevel })
            }
          >
            <Select.Option value="AUTO">AUTO</Select.Option>
            <Select.Option value="SMART">SMART</Select.Option>
            <Select.Option value="ALWAYS">ALWAYS</Select.Option>
            <Select.Option value="NEVER">NEVER</Select.Option>
          </Select>
          <Button onClick={() => openRuleModal()}>
            {t("wecomTenants.addRule")}
          </Button>
          <Button type="primary" loading={saving} onClick={saveSecurity}>
            {t("common.save")}
          </Button>
        </div>
        <Table
          columns={columns}
          dataSource={value.tool_guard_rules || []}
          rowKey={(rule, index) => rule.id || String(index)}
          pagination={false}
          size="small"
        />
        <Input.TextArea
          value={advancedJson}
          onChange={(event) => setAdvancedJson(event.target.value)}
          onBlur={applyAdvancedJson}
          autoSize={{ minRows: 5, maxRows: 10 }}
        />
      </div>

      <Modal
        title={
          editingIndex === null
            ? t("wecomTenants.addRule")
            : t("wecomTenants.editRule")
        }
        open={ruleModalOpen}
        onCancel={() => setRuleModalOpen(false)}
        onOk={saveRule}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="id"
            label={t("wecomTenants.ruleName")}
            rules={[{ required: true, message: t("wecomTenants.required") }]}
          >
            <Input />
          </Form.Item>
          <Form.Item name="toolsText" label={t("wecomTenants.ruleTools")}>
            <Input.TextArea autoSize={{ minRows: 2, maxRows: 5 }} />
          </Form.Item>
          <Form.Item name="severity" label={t("wecomTenants.ruleAction")}>
            <Select>
              <Select.Option value="LOW">LOW</Select.Option>
              <Select.Option value="MEDIUM">MEDIUM</Select.Option>
              <Select.Option value="HIGH">HIGH</Select.Option>
              <Select.Option value="CRITICAL">CRITICAL</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="conditionsJson"
            label={t("wecomTenants.ruleConditions")}
          >
            <Input.TextArea autoSize={{ minRows: 6, maxRows: 12 }} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
