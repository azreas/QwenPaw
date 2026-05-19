import { Form, InputNumber, Select, Card, Alert, Switch } from "antd";
import { useTranslation } from "react-i18next";

const LANGUAGE_OPTIONS = [
  { value: "zh", label: "中文" },
  { value: "en", label: "English" },
  { value: "ru", label: "Русский" },
];

const MEMORY_MANAGER_BACKEND_OPTIONS = [
  { value: "remelight", label: "ReMeLight" },
];

interface ReactAgentCardProps {
  language: string;
  savingLang: boolean;
  onLanguageChange: (value: string) => void;
  timezone: string;
  savingTimezone: boolean;
  onTimezoneChange: (value: string) => void;
}

const TIMEZONES = [
  { value: "UTC", label: "UTC" },
  { value: "Asia/Shanghai", label: "Asia/Shanghai (UTC+8)" },
  { value: "Asia/Tokyo", label: "Asia/Tokyo (UTC+9)" },
  { value: "America/New_York", label: "America/New_York (UTC-5)" },
  { value: "America/Los_Angeles", label: "America/Los_Angeles (UTC-8)" },
  { value: "Europe/London", label: "Europe/London (UTC+0)" },
  { value: "Europe/Paris", label: "Europe/Paris (UTC+1)" },
];

export function ReactAgentCard({
  language,
  savingLang,
  onLanguageChange,
  timezone,
  savingTimezone,
  onTimezoneChange,
}: ReactAgentCardProps) {
  const { t } = useTranslation();

  return (
    <Card title={t("agentConfig.reactAgentTitle")}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
        <Form.Item
          label={t("agentConfig.language")}
          tooltip={t("agentConfig.languageTooltip")}
          style={{ marginBottom: 0 }}
        >
          <Select
            value={language}
            options={LANGUAGE_OPTIONS}
            onChange={onLanguageChange}
            loading={savingLang}
            disabled={savingLang}
          />
        </Form.Item>

        <Form.Item
          label={t("agentConfig.timezone")}
          tooltip={t("agentConfig.timezoneTooltip")}
          style={{ marginBottom: 0 }}
        >
          <Select
            showSearch
            value={timezone}
            placeholder={t("agentConfig.selectTimezone")}
            filterOption={(input, option) =>
              (option?.label?.toString() || "")
                .toLowerCase()
                .includes(input.toLowerCase())
            }
            options={TIMEZONES}
            onChange={onTimezoneChange}
            loading={savingTimezone}
            disabled={savingTimezone}
          />
        </Form.Item>

        <Form.Item
          label={t("agentConfig.maxIters")}
          name="max_iters"
          rules={[
            { required: true, message: t("agentConfig.maxItersRequired") },
            { type: "number", min: 1, message: t("agentConfig.maxItersMin") },
          ]}
          tooltip={t("agentConfig.maxItersTooltip")}
          style={{ marginBottom: 0 }}
        >
          <InputNumber
            min={1}
            placeholder={t("agentConfig.maxItersPlaceholder")}
            style={{ width: "100%" }}
          />
        </Form.Item>
      </div>

      <Form.Item
        label={t("agentConfig.autoContinueOnTextOnly")}
        name="auto_continue_on_text_only"
        valuePropName="checked"
        tooltip={t("agentConfig.autoContinueOnTextOnlyTooltip")}
        style={{ marginTop: 16 }}
      >
        <Switch />
      </Form.Item>

      <Form.Item
        label={t("agentConfig.memoryManagerBackend")}
        name="memory_manager_backend"
        tooltip={t("agentConfig.memoryManagerBackendTooltip")}
      >
        <Select options={MEMORY_MANAGER_BACKEND_OPTIONS} />
      </Form.Item>
      
      <Alert
        type="warning"
        message={t("agentConfig.memoryManagerBackendRestartWarning")}
        style={{ marginBottom: 16 }}
      />

      <Form.Item
        label={t("agentConfig.maxContextLength")}
        name="max_input_length"
        rules={[
          { required: true, message: t("agentConfig.maxContextLengthRequired") },
          { type: "number", min: 1000, message: t("agentConfig.maxContextLengthMin") },
        ]}
        tooltip={t("agentConfig.maxContextLengthTooltip")}
      >
        <InputNumber
          min={1000}
          step={1024}
          placeholder={t("agentConfig.maxContextLengthPlaceholder")}
          style={{ width: "100%" }}
        />
      </Form.Item>
    </Card>
  );
}
