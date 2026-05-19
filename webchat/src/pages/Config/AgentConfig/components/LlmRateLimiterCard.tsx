import { Card, Form, InputNumber } from "antd";
import { useTranslation } from "react-i18next";

export function LlmRateLimiterCard() {
  const { t } = useTranslation();
  const form = Form.useFormInstance();

  return (
    <Card title={t("agentConfig.llmRateLimiterTitle")}>
      <Form.Item
        label={t("agentConfig.llmMaxConcurrent")}
        name="llm_max_concurrent"
        rules={[
          { required: true, message: t("agentConfig.llmMaxConcurrentRequired") },
          { type: "number", min: 1, message: t("agentConfig.llmMaxConcurrentRange") },
        ]}
        tooltip={t("agentConfig.llmMaxConcurrentTooltip")}
      >
        <InputNumber min={1} step={1} placeholder={t("agentConfig.llmMaxConcurrentPlaceholder")} style={{ width: "100%" }} />
      </Form.Item>

      <Form.Item
        label={t("agentConfig.llmMaxQpm")}
        name="llm_max_qpm"
        rules={[
          { required: true, message: t("agentConfig.llmMaxQpmRequired") },
          { type: "number", min: 0, message: t("agentConfig.llmMaxQpmRange") },
        ]}
        tooltip={t("agentConfig.llmMaxQpmTooltip")}
      >
        <InputNumber min={0} step={10} placeholder={t("agentConfig.llmMaxQpmPlaceholder")} style={{ width: "100%" }} />
      </Form.Item>

      <Form.Item
        label={t("agentConfig.llmRateLimitPause")}
        name="llm_rate_limit_pause"
        rules={[
          { required: true, message: t("agentConfig.llmRateLimitPauseRequired") },
          { type: "number", min: 1.0, message: t("agentConfig.llmRateLimitPauseMin") },
        ]}
        tooltip={t("agentConfig.llmRateLimitPauseTooltip")}
      >
        <InputNumber step={0.5} placeholder={t("agentConfig.llmRateLimitPausePlaceholder")} style={{ width: "100%" }} />
      </Form.Item>

      <Form.Item
        label={t("agentConfig.llmRateLimitJitter")}
        name="llm_rate_limit_jitter"
        rules={[
          { required: true, message: t("agentConfig.llmRateLimitJitterRequired") },
          { type: "number", min: 0.0, message: t("agentConfig.llmRateLimitJitterMin") },
        ]}
        tooltip={t("agentConfig.llmRateLimitJitterTooltip")}
      >
        <InputNumber step={0.5} placeholder={t("agentConfig.llmRateLimitJitterPlaceholder")} style={{ width: "100%" }} />
      </Form.Item>

      <Form.Item
        label={t("agentConfig.llmAcquireTimeout")}
        name="llm_acquire_timeout"
        dependencies={["llm_rate_limit_pause", "llm_rate_limit_jitter"]}
        rules={[
          { required: true, message: t("agentConfig.llmAcquireTimeoutRequired") },
          { type: "number", min: 10.0, message: t("agentConfig.llmAcquireTimeoutMin") },
          {
            validator: async (_, value) => {
              const pause = form.getFieldValue("llm_rate_limit_pause");
              const jitter = form.getFieldValue("llm_rate_limit_jitter");
              if (
                typeof value !== "number" ||
                typeof pause !== "number" ||
                typeof jitter !== "number" ||
                value > pause + jitter
              ) {
                return;
              }
              throw new Error(t("agentConfig.llmAcquireTimeoutGtPauseJitter"));
            },
          },
        ]}
        tooltip={t("agentConfig.llmAcquireTimeoutTooltip")}
      >
        <InputNumber step={10} placeholder={t("agentConfig.llmAcquireTimeoutPlaceholder")} style={{ width: "100%" }} />
      </Form.Item>
    </Card>
  );
}
