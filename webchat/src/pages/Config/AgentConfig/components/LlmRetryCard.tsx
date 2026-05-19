import { Card, Form, InputNumber, Switch } from "antd";
import { useTranslation } from "react-i18next";

interface LlmRetryCardProps {
  llmRetryEnabled?: boolean;
}

export function LlmRetryCard({ llmRetryEnabled = true }: LlmRetryCardProps) {
  const { t } = useTranslation();
  const form = Form.useFormInstance();

  return (
    <Card title={t("agentConfig.llmRetryTitle")}>
      <Form.Item
        name="llm_retry_enabled"
        label={t("agentConfig.llmRetryEnabled")}
        valuePropName="checked"
        tooltip={t("agentConfig.llmRetryEnabledTooltip")}
      >
        <Switch />
      </Form.Item>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
        <Form.Item
          label={t("agentConfig.llmMaxRetries")}
          name="llm_max_retries"
          rules={[
            { required: true, message: t("agentConfig.llmMaxRetriesRequired") },
            { type: "number", min: 1, message: t("agentConfig.llmMaxRetriesMin") },
          ]}
          tooltip={t("agentConfig.llmMaxRetriesTooltip")}
          style={{ marginBottom: 0 }}
        >
          <InputNumber
            min={1}
            step={1}
            disabled={!llmRetryEnabled}
            placeholder={t("agentConfig.llmMaxRetriesPlaceholder")}
            style={{ width: "100%" }}
          />
        </Form.Item>

        <Form.Item
          label={t("agentConfig.llmBackoffBase")}
          name="llm_backoff_base"
          rules={[
            { required: true, message: t("agentConfig.llmBackoffBaseRequired") },
            { type: "number", min: 0.1, message: t("agentConfig.llmBackoffBaseMin") },
          ]}
          tooltip={t("agentConfig.llmBackoffBaseTooltip")}
          style={{ marginBottom: 0 }}
        >
          <InputNumber
            step={0.1}
            disabled={!llmRetryEnabled}
            placeholder={t("agentConfig.llmBackoffBasePlaceholder")}
            style={{ width: "100%" }}
          />
        </Form.Item>

        <Form.Item
          label={t("agentConfig.llmBackoffCap")}
          name="llm_backoff_cap"
          dependencies={["llm_backoff_base"]}
          rules={[
            { required: true, message: t("agentConfig.llmBackoffCapRequired") },
            { type: "number", min: 0.5, message: t("agentConfig.llmBackoffCapMin") },
            {
              validator: async (_, value) => {
                const backoffBase = form.getFieldValue("llm_backoff_base");
                if (
                  typeof value !== "number" ||
                  typeof backoffBase !== "number" ||
                  value >= backoffBase
                ) {
                  return;
                }
                throw new Error(t("agentConfig.llmBackoffCapGteBase"));
              },
            },
          ]}
          tooltip={t("agentConfig.llmBackoffCapTooltip")}
          style={{ marginBottom: 0 }}
        >
          <InputNumber
            step={0.5}
            disabled={!llmRetryEnabled}
            placeholder={t("agentConfig.llmBackoffCapPlaceholder")}
            style={{ width: "100%" }}
          />
        </Form.Item>
      </div>
    </Card>
  );
}
