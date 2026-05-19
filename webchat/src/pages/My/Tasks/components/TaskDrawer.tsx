import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Button, Drawer, Form, Input, Select, Switch } from "antd";
import type { WebchatTask } from "../../../../api/types/tasks";
import {
  DEFAULT_TASK_FORM,
  formToTask,
  taskToForm,
  type TaskFormValues,
} from "./taskForm";

interface TaskDrawerProps {
  open: boolean;
  task?: WebchatTask | null;
  saving: boolean;
  onClose: () => void;
  onSubmit: (task: WebchatTask) => Promise<void>;
}

const timezoneOptions = [
  "Asia/Shanghai",
  "UTC",
  "America/New_York",
  "Europe/London",
  "Asia/Tokyo",
].map((value) => ({ value, label: value }));

export default function TaskDrawer({
  open,
  task,
  saving,
  onClose,
  onSubmit,
}: TaskDrawerProps) {
  const { t } = useTranslation();
  const [form] = Form.useForm<TaskFormValues>();
  const taskType = Form.useWatch("task_type", form);

  useEffect(() => {
    if (!open) return;
    form.setFieldsValue(task ? taskToForm(task) : DEFAULT_TASK_FORM);
  }, [form, open, task]);

  const handleSave = async () => {
    const values = await form.validateFields();
    await onSubmit(formToTask(values, task));
  };

  return (
    <Drawer
      title={task ? t("tasks.editTask") : t("tasks.createTask")}
      width={480}
      open={open}
      onClose={onClose}
      destroyOnClose
      footer={
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <Button onClick={onClose}>{t("common.cancel")}</Button>
          <Button type="primary" loading={saving} onClick={handleSave}>
            {t("common.save")}
          </Button>
        </div>
      }
    >
      <Form<TaskFormValues>
        form={form}
        layout="vertical"
        initialValues={DEFAULT_TASK_FORM}
      >
        <Form.Item
          name="name"
          label={t("tasks.name")}
          rules={[{ required: true, message: t("tasks.nameRequired") }]}
        >
          <Input placeholder={t("tasks.namePlaceholder")} />
        </Form.Item>

        <Form.Item
          name="enabled"
          label={t("tasks.enabled")}
          valuePropName="checked"
        >
          <Switch />
        </Form.Item>

        <Form.Item name="task_type" label={t("tasks.type")}>
          <Select
            options={[
              { value: "agent", label: t("tasks.typeAgent") },
              { value: "text", label: t("tasks.typeText") },
            ]}
          />
        </Form.Item>

        <Form.Item
          name="content"
          label={taskType === "text" ? t("tasks.message") : t("tasks.prompt")}
          rules={[{ required: true, message: t("tasks.contentRequired") }]}
        >
          <Input.TextArea
            rows={6}
            placeholder={
              taskType === "text"
                ? t("tasks.messagePlaceholder")
                : t("tasks.promptPlaceholder")
            }
          />
        </Form.Item>

        <Form.Item
          name="cron"
          label={t("tasks.cron")}
          rules={[{ required: true, message: t("tasks.cronRequired") }]}
        >
          <Input placeholder="0 9 * * *" />
        </Form.Item>

        <Form.Item name="timezone" label={t("tasks.timezone")}>
          <Select options={timezoneOptions} />
        </Form.Item>

        <Form.Item
          name="timeout_seconds"
          label={t("tasks.timeoutSeconds")}
          rules={[{ required: true, message: t("tasks.timeoutRequired") }]}
        >
          <Input type="number" min={1} />
        </Form.Item>
      </Form>
    </Drawer>
  );
}
