import { Alert } from "@agentscope-ai/design";
import { Form, Input, Modal, Select, Switch } from "@agentscope-ai/design";
import { useTranslation } from "react-i18next";
import styles from "../../index.module.less";
import type { CronFormValues } from "./tenantCronForm";
import { DEFAULT_JOB } from "./tenantCronForm";

interface Props {
  open: boolean;
  editing: boolean;
  saving: boolean;
  error: string | null;
  form: ReturnType<typeof Form.useForm<CronFormValues>>[0];
  onCancel: () => void;
  onSave: () => Promise<void>;
}

export function TenantCronJobModal({
  open,
  editing,
  saving,
  error,
  form,
  onCancel,
  onSave,
}: Props) {
  const { t } = useTranslation();

  return (
    <Modal
      title={editing ? t("wecomTenants.editJob") : t("wecomTenants.createJob")}
      open={open}
      width={780}
      onCancel={onCancel}
      onOk={onSave}
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
      <Form form={form} layout="vertical" initialValues={DEFAULT_JOB}>
        <div className={styles.modalFormGrid}>
          <Form.Item name="id" label="ID">
            <Input disabled={editing} />
          </Form.Item>
          <Form.Item
            name="name"
            label={t("wecomTenants.name")}
            rules={[{ required: true, message: t("wecomTenants.required") }]}
          >
            <Input />
          </Form.Item>
        </div>
        <div className={styles.modalFormGrid}>
          <Form.Item
            name="cron"
            label={t("wecomTenants.cron")}
            rules={[{ required: true, message: t("wecomTenants.required") }]}
          >
            <Input placeholder="0 9 * * *" />
          </Form.Item>
          <Form.Item name="timezone" label={t("wecomTenants.timezone")}>
            <Input placeholder="UTC" />
          </Form.Item>
        </div>
        <div className={styles.modalFormGrid}>
          <Form.Item name="task_type" label={t("wecomTenants.taskType")}>
            <Select>
              <Select.Option value="text">text</Select.Option>
              <Select.Option value="agent">agent</Select.Option>
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
        <Form.Item name="text" label={t("wecomTenants.text")}>
          <Input.TextArea autoSize={{ minRows: 3, maxRows: 6 }} />
        </Form.Item>
        <div className={styles.modalFormGrid}>
          <Form.Item name="channel" label={t("wecomTenants.channel")}>
            <Input placeholder="console" />
          </Form.Item>
          <Form.Item name="mode" label={t("wecomTenants.dispatchMode")}>
            <Select>
              <Select.Option value="stream">stream</Select.Option>
              <Select.Option value="final">final</Select.Option>
            </Select>
          </Form.Item>
        </div>
        <div className={styles.modalFormGrid}>
          <Form.Item
            name="user_id"
            label={t("wecomTenants.dispatchUser")}
            rules={[{ required: true, message: t("wecomTenants.required") }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="session_id"
            label={t("wecomTenants.dispatchSession")}
            rules={[{ required: true, message: t("wecomTenants.required") }]}
          >
            <Input />
          </Form.Item>
        </div>
        <Form.Item name="advancedJson" label={t("wecomTenants.advancedJson")}>
          <Input.TextArea autoSize={{ minRows: 5, maxRows: 10 }} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
