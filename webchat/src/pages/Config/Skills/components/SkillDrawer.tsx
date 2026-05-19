import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Drawer, Form, Input, Select, Switch, Button, message, Space } from "antd";
import type { SkillSpec } from "../../../../api/modules/agent";

const { TextArea } = Input;

export interface SkillDrawerFormValues {
  name: string;
  description?: string;
  content: string;
  enabled?: boolean;
  channels?: string[];
  tags?: string[];
  config?: Record<string, unknown>;
}

interface SkillDrawerProps {
  open: boolean;
  skill: SkillSpec | null;
  onClose: () => void;
  onSave: (values: SkillDrawerFormValues) => Promise<void>;
  isDark?: boolean;
}

export function SkillDrawer({ open, skill, onClose, onSave }: SkillDrawerProps) {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);

  // 使用国际化渠道选项
  const channelOptions = [
    { label: t("skills.channelAll"), value: "all" },
    { label: t("skills.channelConsole"), value: "console" },
    { label: t("skills.channelWebchat"), value: "webchat" },
    { label: t("skills.channelDiscord"), value: "discord" },
    { label: t("skills.channelTelegram"), value: "telegram" },
    { label: t("skills.channelDingtalk"), value: "dingtalk" },
    { label: t("skills.channelFeishu"), value: "feishu" },
  ];

  useEffect(() => {
    if (skill) {
      form.setFieldsValue({
        name: skill.name,
        description: skill.description,
        content: skill.content,
        enabled: skill.enabled,
        channels: skill.channels || ["all"],
        tags: skill.tags || [],
        config: skill.config ? JSON.stringify(skill.config, null, 2) : "{}",
      });
    } else {
      form.resetFields();
      form.setFieldsValue({
        enabled: true,
        channels: ["all"],
        tags: [],
        config: "{}",
      });
    }
  }, [skill, form, open]);

  // Frontmatter验证
  const validateFrontmatter = async (_: any, value: string) => {
    if (!value || !value.trim()) {
      throw new Error(t("skills.contentRequired"));
    }
    
    // 检查是否包含frontmatter（以---开头和结尾的YAML元数据）
    const trimmed = value.trim();
    if (!trimmed.startsWith("---")) {
      throw new Error(t("skills.frontmatterRequired"));
    }
    
    // 检查是否有至少两个---分隔符
    const parts = trimmed.split("---");
    if (parts.length < 3) {
      throw new Error(t("skills.frontmatterFormat"));
    }
    
    // 尝试解析frontmatter中的name和description
    try {
      const fmContent = parts[1];
      const nameMatch = fmContent.match(/^name:\s*(.+)$/m);
      const descMatch = fmContent.match(/^description:\s*(.+)$/m);
      
      if (!nameMatch) {
        throw new Error(t("skills.frontmatterNameRequired"));
      }
      if (!descMatch) {
        throw new Error(t("skills.frontmatterDescriptionRequired"));
      }
    } catch (e) {
      if (e instanceof Error) {
        throw e;
      }
      throw new Error(t("skills.frontmatterInvalid"));
    }
  };

  // 验证JSON格式的配置
  const validateConfig = async (_: any, value: string) => {
    if (!value || !value.trim()) {
      return Promise.resolve();
    }
    
    try {
      JSON.parse(value);
      return Promise.resolve();
    } catch (e) {
      throw new Error(t("skills.invalidConfig"));
    }
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      
      // 解析config字段
      if (values.config && typeof values.config === "string") {
        try {
          values.config = JSON.parse(values.config);
        } catch (e) {
          message.error(t("skills.invalidConfig"));
          return;
        }
      }
      
      setSaving(true);
      await onSave(values);
      message.success(skill ? t("skills.updatedSuccessfully") : t("skills.createdSuccessfully"));
      onClose();
    } catch (error: any) {
      console.error("Save failed:", error);
      if (error.errorFields) {
        // 表单验证错误
        message.error(error.errorFields[0]?.errors[0]);
      } else {
        message.error(t("common.error"));
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <Drawer
      title={skill ? t("skills.editSkill") : t("skills.createSkill")}
      open={open}
      onClose={onClose}
      width={700}
      extra={
        <Space>
          <Button onClick={onClose}>{t("common.cancel")}</Button>
          <Button type="primary" loading={saving} onClick={handleSave}>
            {t("common.save")}
          </Button>
        </Space>
      }
    >
      <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
        <Form.Item
          name="name"
          label={t("skills.name")}
          rules={[
            { required: true, message: t("common.required") },
            { pattern: /^[a-zA-Z0-9_-]+$/, message: t("skills.namePattern") },
          ]}
        >
          <Input
            disabled={!!skill}
            placeholder={t("skills.namePlaceholder")}
          />
        </Form.Item>

        <Form.Item
          name="description"
          label={t("skills.description")}
        >
          <Input placeholder={t("skills.descriptionPlaceholder")} />
        </Form.Item>

        <Form.Item
          name="content"
          label={t("skills.content")}
          rules={[
            { required: true, message: t("skills.contentRequired") },
            { validator: validateFrontmatter },
          ]}
        >
          <TextArea
            rows={15}
            placeholder={t("skills.contentPlaceholder")}
            style={{ fontFamily: "monospace", fontSize: 13 }}
          />
        </Form.Item>

        <Form.Item
          name="channels"
          label={t("skills.channels")}
        >
          <Select
            mode="multiple"
            options={channelOptions}
            placeholder={t("skills.channelsPlaceholder")}
            allowClear
          />
        </Form.Item>

        <Form.Item
          name="tags"
          label={t("skills.tags")}
        >
          <Select
            mode="tags"
            placeholder={t("skills.tagsPlaceholder")}
            allowClear
          />
        </Form.Item>

        <Form.Item
          name="config"
          label={t("skills.config")}
          rules={[{ validator: validateConfig }]}
        >
          <TextArea
            rows={5}
            placeholder={t("skills.configPlaceholder")}
            style={{ fontFamily: "monospace", fontSize: 13 }}
          />
        </Form.Item>

        <Form.Item
          name="enabled"
          label={t("skills.enable")}
          valuePropName="checked"
        >
          <Switch
            checkedChildren={t("common.enabled")}
            unCheckedChildren={t("common.disabled")}
          />
        </Form.Item>
      </Form>
    </Drawer>
  );
}
