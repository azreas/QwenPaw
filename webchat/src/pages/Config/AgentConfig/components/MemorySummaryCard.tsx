import { Form, Card, Switch, InputNumber, Input } from "antd";
import { useTranslation } from "react-i18next";
import { SliderWithValue } from "./SliderWithValue";

export function MemorySummaryCard() {
  const { t } = useTranslation();

  return (
    <Card title={t("agentConfig.memorySummaryTitle")}>
      <Form.Item
        label={t("agentConfig.memorySummaryEnabled")}
        name={["memory_summary", "memory_summary_enabled"]}
        valuePropName="checked"
        tooltip={t("agentConfig.memorySummaryEnabledTooltip")}
      >
        <Switch />
      </Form.Item>

      <Form.Item
        label={t("agentConfig.dreamCron")}
        name={["memory_summary", "dream_cron"]}
        tooltip={t("agentConfig.dreamCronTooltip")}
      >
        <Input placeholder={t("agentConfig.dreamCronPlaceholder")} />
      </Form.Item>

      <Form.Item
        label={t("agentConfig.forceMemorySearch")}
        name={["memory_summary", "force_memory_search"]}
        valuePropName="checked"
        tooltip={t("agentConfig.forceMemorySearchTooltip")}
      >
        <Switch />
      </Form.Item>

      <Form.Item
        label={t("agentConfig.forceMaxResults")}
        name={["memory_summary", "force_max_results"]}
        rules={[
          { required: true, message: t("agentConfig.forceMaxResultsRequired") },
          { type: "number", min: 1, message: t("agentConfig.forceMaxResultsMin") },
        ]}
        tooltip={t("agentConfig.forceMaxResultsTooltip")}
      >
        <InputNumber min={1} step={1} style={{ width: "100%" }} />
      </Form.Item>

      <Form.Item
        label={t("agentConfig.forceMinScore")}
        name={["memory_summary", "force_min_score"]}
        rules={[{ required: true, message: t("agentConfig.forceMinScoreRequired") }]}
        tooltip={t("agentConfig.forceMinScoreTooltip")}
      >
        <SliderWithValue
          min={0}
          max={1}
          step={0.05}
          marks={{ 0: "0", 0.5: "0.5", 1: "1" }}
        />
      </Form.Item>

      <Form.Item
        label={t("agentConfig.rebuildMemoryIndexOnStart")}
        name={["memory_summary", "rebuild_memory_index_on_start"]}
        valuePropName="checked"
        tooltip={t("agentConfig.rebuildMemoryIndexOnStartTooltip")}
      >
        <Switch />
      </Form.Item>
    </Card>
  );
}
