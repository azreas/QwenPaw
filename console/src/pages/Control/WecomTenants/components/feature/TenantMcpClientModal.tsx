import { useEffect, useState } from "react";
import { Alert } from "@agentscope-ai/design";
import { Form, Input, Modal, Select, Switch } from "@agentscope-ai/design";
import { useTranslation } from "react-i18next";
import { wecomTenantApi } from "../../../../../api/modules/wecomTenant";
import type {
  WecomMcpTransport,
  WecomTenantMcpClient,
} from "../../../../../api/types";
import { useAppMessage } from "../../../../../hooks/useAppMessage";
import styles from "../../index.module.less";

interface Props {
  agentId: string;
  open: boolean;
  client: WecomTenantMcpClient | null;
  onClose: () => void;
  onSaved: () => Promise<void>;
}

interface McpFormValues {
  client_key: string;
  name: string;
  description: string;
  enabled: boolean;
  transport: WecomMcpTransport;
  url: string;
  command: string;
  argsText: string;
  cwd: string;
  envJson: string;
  headersJson: string;
}

function prettyJson(value: unknown): string {
  return JSON.stringify(value ?? {}, null, 2);
}

function lines(value: string): string[] {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseObject(raw: string, label: string): Record<string, string> {
  const parsed = JSON.parse(raw || "{}") as unknown;
  if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
    throw new Error(`${label} must be a JSON object`);
  }
  return Object.fromEntries(
    Object.entries(parsed as Record<string, unknown>).map(([key, value]) => [
      key,
      String(value),
    ]),
  );
}

function emptyClient(): McpFormValues {
  return {
    client_key: "",
    name: "",
    description: "",
    enabled: true,
    transport: "stdio",
    url: "",
    command: "",
    argsText: "",
    cwd: "",
    envJson: "{}",
    headersJson: "{}",
  };
}

function clientToForm(client: WecomTenantMcpClient): McpFormValues {
  return {
    client_key: client.client_key,
    name: client.name,
    description: client.description || "",
    enabled: client.enabled,
    transport: client.transport || "stdio",
    url: client.url || "",
    command: client.command || "",
    argsText: (client.args || []).join("\n"),
    cwd: client.cwd || "",
    envJson: prettyJson(client.env || {}),
    headersJson: prettyJson(client.headers || {}),
  };
}

export function TenantMcpClientModal({
  agentId,
  open,
  client,
  onClose,
  onSaved,
}: Props) {
  const { t } = useTranslation();
  const { message } = useAppMessage();
  const [form] = Form.useForm<McpFormValues>();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const transport = Form.useWatch("transport", form) as WecomMcpTransport;

  useEffect(() => {
    if (!open) return;
    setError(null);
    form.setFieldsValue(client ? clientToForm(client) : emptyClient());
  }, [client, form, open]);

  const saveClient = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      const payload = {
        name: values.name,
        description: values.description || "",
        enabled: values.enabled,
        transport: values.transport,
        url: values.transport === "stdio" ? "" : values.url || "",
        command: values.transport === "stdio" ? values.command || "" : "",
        args: values.transport === "stdio" ? lines(values.argsText || "") : [],
        cwd: values.transport === "stdio" ? values.cwd || "" : "",
        env: values.transport === "stdio"
          ? parseObject(values.envJson, "env")
          : {},
        headers: values.transport === "stdio"
          ? {}
          : parseObject(values.headersJson, "headers"),
      };
      if (client) {
        await wecomTenantApi.updateWecomTenantMcp(
          agentId,
          client.client_key,
          payload,
        );
      } else {
        await wecomTenantApi.createWecomTenantMcp(agentId, {
          client_key: values.client_key,
          client: payload,
        });
      }
      message.success(t("wecomTenants.configSavedReloaded"));
      onClose();
      await onSaved();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      title={client ? t("wecomTenants.editMcp") : t("wecomTenants.createMcp")}
      open={open}
      width={760}
      onCancel={onClose}
      onOk={saveClient}
      confirmLoading={saving}
      destroyOnClose
    >
      {error && (
        <Alert
          className={styles.inlineAlert}
          type="error"
          showIcon
          message={t("wecomTenants.configError")}
          description={error}
        />
      )}
      <Form form={form} layout="vertical" initialValues={emptyClient()}>
        <div className={styles.modalFormGrid}>
          <Form.Item
            name="client_key"
            label={t("wecomTenants.clientKey")}
            rules={[{ required: true, message: t("wecomTenants.required") }]}
          >
            <Input disabled={!!client} />
          </Form.Item>
          <Form.Item
            name="name"
            label={t("wecomTenants.name")}
            rules={[{ required: true, message: t("wecomTenants.required") }]}
          >
            <Input />
          </Form.Item>
        </div>
        <Form.Item name="description" label={t("wecomTenants.description")}>
          <Input />
        </Form.Item>
        <div className={styles.modalFormGrid}>
          <Form.Item name="transport" label={t("wecomTenants.transport")}>
            <Select>
              <Select.Option value="stdio">stdio</Select.Option>
              <Select.Option value="streamable_http">streamable_http</Select.Option>
              <Select.Option value="sse">sse</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="enabled"
            label={t("wecomTenants.enabled")}
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
        </div>
        {transport === "stdio" ? (
          <>
            <Form.Item name="command" label={t("wecomTenants.command")}>
              <Input />
            </Form.Item>
            <Form.Item name="argsText" label={t("wecomTenants.args")}>
              <Input.TextArea autoSize={{ minRows: 3, maxRows: 8 }} />
            </Form.Item>
            <Form.Item name="cwd" label={t("wecomTenants.cwd")}>
              <Input />
            </Form.Item>
            <Form.Item name="envJson" label={t("wecomTenants.envJson")}>
              <Input.TextArea autoSize={{ minRows: 4, maxRows: 10 }} />
            </Form.Item>
          </>
        ) : (
          <>
            <Form.Item
              name="url"
              label={t("wecomTenants.url")}
              rules={[{ required: true, message: t("wecomTenants.required") }]}
            >
              <Input />
            </Form.Item>
            <Form.Item name="headersJson" label={t("wecomTenants.headersJson")}>
              <Input.TextArea autoSize={{ minRows: 4, maxRows: 10 }} />
            </Form.Item>
          </>
        )}
      </Form>
    </Modal>
  );
}
